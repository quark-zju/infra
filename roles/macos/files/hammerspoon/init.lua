local targetDeviceName = "AirPods Pro"  -- your device name
local targetVolume = 10
local lastDeviceName = ""

function audioDeviceChanged()
    local current = hs.audiodevice.defaultOutputDevice()
    local name = current:name()

    if name ~= lastDeviceName then
        lastDeviceName = name
        if string.find(name, targetDeviceName) then
            current:setVolume(targetVolume)
            hs.alert.show(targetDeviceName .. " connected, set volume to: " .. targetVolume)
        end
    end
end

hs.audiodevice.watcher.setCallback(audioDeviceChanged)
hs.audiodevice.watcher:start()

-- blueutil is installed by the macOS Ansible role. GUI apps may have a minimal PATH.
local bluetoothLog = hs.logger.new("sonySleep", "info")
local blueutilPath
for _, path in ipairs({"/opt/homebrew/bin/blueutil", "/usr/local/bin/blueutil"}) do
    if hs.fs.attributes(path, "mode") == "file" then
        blueutilPath = path
        break
    end
end

-- Add Bluetooth addresses here for Sony headphones with custom names.
-- Use lowercase, hyphen-separated addresses, e.g. ["aa-bb-cc-dd-ee-ff"] = true.
local sonyHeadphoneAddresses = {}

local function isSonyHeadphone(device)
    local name = (device.name or ""):upper()
    name = name:gsub("^LE[_ %-]*", ""):gsub("^SONY[_ %-]*", "")
    return sonyHeadphoneAddresses[(device.address or ""):lower()] == true
        or name:match("^WH%-") ~= nil
        or name:match("^WF%-") ~= nil
        or name:match("^WI%-") ~= nil
        or name:match("^MDR%-") ~= nil
        or name:match("^LINKBUDS") ~= nil
end

local function pairedSonyHeadphones()
    local output, success = hs.execute(blueutilPath .. " --paired --format json")
    if not success then
        bluetoothLog.e("Cannot list paired Bluetooth devices: " .. output)
        return {}
    end
    local decoded, devices = pcall(hs.json.decode, output)
    if not decoded or type(devices) ~= "table" then
        bluetoothLog.e("Invalid paired Bluetooth device JSON")
        return {}
    end
    local headphones = {}
    for _, device in ipairs(devices) do
        if isSonyHeadphone(device) then
            table.insert(headphones, device)
        end
    end
    return headphones
end

if blueutilPath then
    for _, device in ipairs(pairedSonyHeadphones()) do
        bluetoothLog.i("Registered Sony headphones: " .. (device.name or device.address))
    end

    -- Keep a global reference so the watcher survives garbage collection.
    sonyHeadphoneSleepWatcher = hs.caffeinate.watcher.new(function(event)
        if event ~= hs.caffeinate.watcher.systemWillSleep then
            return
        end
        -- Refresh on every sleep to include newly paired headphones. Run synchronously
        -- so disconnect commands execute before this sleep callback returns.
        for _, device in ipairs(pairedSonyHeadphones()) do
            local address = device.address or ""
            if device.connected == true and address:match("^%x%x%-%x%x%-%x%x%-%x%x%-%x%x%-%x%x$") then
                local output, success = hs.execute(blueutilPath .. " --disconnect " .. address)
                if success then
                    bluetoothLog.i("Disconnected: " .. (device.name or address))
                else
                    bluetoothLog.e("Cannot disconnect " .. address .. ": " .. output)
                end
            end
        end
    end)
    sonyHeadphoneSleepWatcher:start()
else
    bluetoothLog.e("blueutil missing; install it with brew install blueutil, then reload Hammerspoon")
end
