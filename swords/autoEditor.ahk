; ===================================================
; Auto Clicker - Image Editor
; Scans autobtn folder for images and auto-clicks them
; Search region: Bottom-right quadrant (most common button area)
; ===================================================

#Requires AutoHotkey v2.0
#SingleInstance Force

; Global Variables
global isRunning := false
global imageFiles := []
global imageCheckboxes := Map()
global imageClickCounts := Map()  ; Track click counts
global statusText := ""
global searchDelay := 500  ; ms between searches

; Main GUI
MainGui := Gui("+AlwaysOnTop", "Auto Clicker - Image Editor")
MainGui.SetFont("s10")

; Status label
StatusLabel := MainGui.Add("Text", "w300 h30 Center", "준비됨")

; Load images from autobtn folder
LoadImages()

; Create checkboxes for each image
yPos := 40
for imgFile in imageFiles {
    fileName := RegExReplace(imgFile, ".*\\", "")  ; Get filename only
    baseName := RegExReplace(fileName, "\.(png|jpg|jpeg|bmp)$", "")  ; Remove extension
    
    cb := MainGui.Add("Checkbox", "x10 y" yPos " w280", baseName)
    cb.Value := 1  ; Checked by default
    imageCheckboxes[imgFile] := cb
    imageClickCounts[imgFile] := 0  ; Initialize counter
    yPos += 30
}

; Start/Stop button
yPos += 10
ToggleBtn := MainGui.Add("Button", "x10 y" yPos " w280 h40", "작업시작")
ToggleBtn.OnEvent("Click", ToggleAutomation)

; Counter display
yPos += 50
CounterLabel := MainGui.Add("Text", "x10 y" yPos " w280 h30 Center", "클릭 횟수: 0")
CounterLabel.SetFont("s9 cGray")

; Initialize counter display
UpdateCounterDisplay()

; Show GUI
MainGui.Show("w300 h" (yPos + 40))

return

; ===================================================
; Functions
; ===================================================

LoadImages() {
    global imageFiles
    
    ; Get script directory
    scriptDir := A_ScriptDir
    autobtnPath := scriptDir "\autobtn"
    
    ; Check if autobtn folder exists
    if !DirExist(autobtnPath) {
        MsgBox("autobtn 폴더를 찾을 수 없습니다.`n폴더를 생성하고 이미지를 추가하세요.", "오류", "IconX")
        ExitApp
    }
    
    ; Load all image files
    Loop Files, autobtnPath "\*.png"
        imageFiles.Push(A_LoopFileFullPath)
    Loop Files, autobtnPath "\*.jpg"
        imageFiles.Push(A_LoopFileFullPath)
    Loop Files, autobtnPath "\*.jpeg"
        imageFiles.Push(A_LoopFileFullPath)
    Loop Files, autobtnPath "\*.bmp"
        imageFiles.Push(A_LoopFileFullPath)
    
    if imageFiles.Length = 0 {
        MsgBox("autobtn 폴더에 이미지 파일이 없습니다.", "경고", "Icon!")
        ExitApp
    }
}

ToggleAutomation(*) {
    global isRunning, ToggleBtn, StatusLabel
    
    isRunning := !isRunning
    
    if isRunning {
        ToggleBtn.Text := "작업중지"
        StatusLabel.Text := "실행중..."
        StatusLabel.SetFont("cGreen")
        SetTimer(SearchAndClickImages, searchDelay)
    } else {
        ToggleBtn.Text := "작업시작"
        StatusLabel.Text := "중지됨"
        StatusLabel.SetFont("cRed")
        SetTimer(SearchAndClickImages, 0)
    }
}

SearchAndClickImages() {
    global imageFiles, imageCheckboxes, StatusLabel, MainGui
    
    if !isRunning
        return
    
    ; Get GUI window position to determine which monitor it's on
    MainGui.GetPos(&guiX, &guiY, &guiW, &guiH)
    guiCenterX := guiX + (guiW // 2)
    guiCenterY := guiY + (guiH // 2)
    
    ; Find which monitor contains the GUI
    monitorFound := false
    monLeft := 0
    monTop := 0
    monRight := A_ScreenWidth
    monBottom := A_ScreenHeight
    
    ; Check all monitors
    MonitorCount := MonitorGetCount()
    Loop MonitorCount {
        MonitorGet(A_Index, &mLeft, &mTop, &mRight, &mBottom)
        
        ; Check if GUI center is within this monitor
        if (guiCenterX >= mLeft && guiCenterX <= mRight && 
            guiCenterY >= mTop && guiCenterY <= mBottom) {
            monLeft := mLeft
            monTop := mTop
            monRight := mRight
            monBottom := mBottom
            monitorFound := true
            break
        }
    }
    
    ; Calculate search region (bottom-right quadrant of GUI's monitor)
    monWidth := monRight - monLeft
    monHeight := monBottom - monTop
    searchX1 := monLeft + (monWidth // 2)
    searchY1 := monTop + (monHeight // 2)
    searchX2 := monRight
    searchY2 := monBottom
    
    ; Search for each checked image
    for imgFile in imageFiles {
        cb := imageCheckboxes[imgFile]
        
        ; Skip if not checked
        if !cb.Value
            continue
        
        ; Get filename for display
        fileName := RegExReplace(imgFile, ".*\\", "")
        baseName := RegExReplace(fileName, "\.(png|jpg|jpeg|bmp)$", "")
        
        ; Update status
        StatusLabel.Text := "검색중: " baseName
        
        ; Search for image in bottom-right quadrant
        try {
            if ImageSearch(&foundX, &foundY, searchX1, searchY1, searchX2, searchY2, "*50 " imgFile) {
                ; Image found! Click it
                StatusLabel.Text := "발견: " baseName " (" foundX "," foundY ")"
                StatusLabel.SetFont("cBlue")
                
                ; Store original mouse position
                MouseGetPos(&origX, &origY)
                
                ; Click the found image
                Click(foundX, foundY)
                
                ; Wait a bit
                Sleep(200)
                
                ; Restore mouse position
                MouseMove(origX, origY)
                
                ; Increment click counter
                global imageClickCounts
                imageClickCounts[imgFile] := imageClickCounts[imgFile] + 1
                UpdateCounterDisplay()
                
                ; Update status
                StatusLabel.Text := "클릭완료: " baseName
                StatusLabel.SetFont("cGreen")
                
                ; Wait before next search
                Sleep(1000)
                return  ; Exit to restart timer
            }
        } catch as err {
            ; Image search failed, continue to next
            continue
        }
    }
    
    ; No images found
    StatusLabel.Text := "대기중... (우하단 검색)"
    StatusLabel.SetFont("cGreen")
}

UpdateCounterDisplay() {
    global imageFiles, imageClickCounts, CounterLabel
    
    ; Build counter text: "filename: count / filename: count"
    counterText := ""
    for imgFile in imageFiles {
        fileName := RegExReplace(imgFile, ".*\\", "")
        baseName := RegExReplace(fileName, "\.(png|jpg|jpeg|bmp)$", "")
        count := imageClickCounts[imgFile]
        
        if (counterText != "")
            counterText .= " / "
        counterText .= baseName ": " count
    }
    
    CounterLabel.Text := counterText
}

; Exit handler
^Esc::ExitApp  ; Ctrl+Esc to exit
