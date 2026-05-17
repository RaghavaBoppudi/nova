import sounddevice as sd

def test_devices():
    devices = sd.query_devices()
    print("Available audio devices:")
    print(devices)
    
    default_input = sd.query_devices(kind='input')
    print(f"\nDefault input device: {default_input['name']}")

if __name__ == "__main__":
    test_devices()
