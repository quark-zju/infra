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
