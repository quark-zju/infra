local targetDeviceName = "AirPods Pro"  -- your device name
local targetVolume = 10
local lastDeviceName = ""
-- Optional ~/.hammerspoon/local.lua example:
-- function volumeLimit(device)
--     if (device:name() or ""):find("AirPods", 1, true) then return 15 end
--     return 30
-- end
local localConfig = hs.configdir .. "/local.lua"
if hs.fs.attributes(localConfig, "mode") == "file" then
    dofile(localConfig)
end

local function effectiveVolumeLimit(device)
    local limit = 20
    if type(volumeLimit) == "function" then
        local ok, value = pcall(volumeLimit, device)
        if ok and type(value) == "number" and value >= 1 and value <= 100 then
            limit = value
        elseif not ok then
            print("volumeLimit failed: " .. tostring(value))
        end
    end
    return math.min(limit, 50)
end
local watchedOutput

local function clampVolume(device)
    if not device then return end
    local maxVolume = effectiveVolumeLimit(device)
    local volume = device:outputVolume()
    if volume and volume > maxVolume and not device:setOutputVolume(maxVolume) then
        print("Unable to limit output volume: " .. (device:name() or "unknown device"))
    end
end

local function watchDefaultOutput()
    if watchedOutput then watchedOutput:watcherStop() end
    watchedOutput = hs.audiodevice.defaultOutputDevice()
    if not watchedOutput then return end

    watchedOutput:watcherCallback(function(uid, event, scope)
        if (event == "vmvc" or event == "volm") and (scope == "outp" or scope == "glob") then
            clampVolume(hs.audiodevice.findDeviceByUID(uid))
        end
    end)
    if not watchedOutput:watcherStart() then
        print("Unable to watch output device: " .. (watchedOutput:name() or "unknown device"))
    end
    clampVolume(watchedOutput)
end

function audioDeviceChanged()
    local current = hs.audiodevice.defaultOutputDevice()
    if not current then
        lastDeviceName = ""
        return
    end
    local name = current:name()
    if not name then
        lastDeviceName = ""
        return
    end

    if name ~= lastDeviceName then
        lastDeviceName = name
        if string.find(name, targetDeviceName) then
            current:setVolume(targetVolume)
            hs.alert.show(targetDeviceName .. " connected, set volume to: " .. targetVolume)
        end
    end
end

hs.audiodevice.watcher.setCallback(function(event)
    audioDeviceChanged()
    if event == "dOut" then watchDefaultOutput() end
end)
hs.audiodevice.watcher:start()
watchDefaultOutput()

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

local function runBlueutil(arguments)
    -- hs.execute otherwise omits stderr, hiding Bluetooth permission failures.
    local output, success, termination, code = hs.execute(blueutilPath .. " " .. arguments .. " 2>&1")
    if not success then
        bluetoothLog.e(string.format("blueutil %s failed (%s %s): %s",
            arguments, tostring(termination), tostring(code), output))
        if code == 69 or code == 134 or (termination == "signal" and code == 6) then
            bluetoothLog.e("Check System Settings > Privacy & Security > Bluetooth: allow Hammerspoon/blueutil, then reload Hammerspoon. Also check that Bluetooth is on.")
        end
    end
    return output, success
end

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
    local output, success = runBlueutil("--format json --paired")
    if not success then
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
                local _, success = runBlueutil("--disconnect " .. address)
                if success then
                    bluetoothLog.i("Disconnected: " .. (device.name or address))
                end
            end
        end
    end)
    sonyHeadphoneSleepWatcher:start()
else
    bluetoothLog.e("blueutil missing; install it with brew install blueutil, then reload Hammerspoon")
end
