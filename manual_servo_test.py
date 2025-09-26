#!/usr/bin/env python3
"""
Manual servo enable test script.
Use this for quick 30-second console tests to find the correct DO bit/polarity.

Usage:
1. Connect to your controller first
2. Run: python manual_servo_test.py
3. Try different DO bits until _MOA flips to 0

Example commands it will try:
MOA; WT 100; SB 1; SH A; MG _MOA
MOA; WT 100; CB 1; SB 2; SH A; MG _MOA
...
"""

def test_servo_enable_bits(controller, axis='A', max_bit=16):
    """
    Test different DO bits to find which one enables the servo.
    Returns the first successful bit and polarity.
    """
    print(f"Testing servo enable for axis {axis}...")
    print("Commands being sent:")
    
    for bit in range(1, max_bit + 1):
        # Test active-high first
        print(f"\nTesting DO{bit} active-high:")
        try:
            controller.send_command(f"MO {axis}")
            controller.send_command("WT 100,0")  # Wait 100ms
            controller.send_command(f"SB {bit}")
            controller.send_command(f"SH {axis}")
            mo_status = controller.send_command(f"MG _MO{axis}")
            print(f"  MO{axis} status: {mo_status}")
            
            if mo_status.strip() == "0":
                print(f"  SUCCESS! DO{bit} active-high enables servo")
                return bit, "active-high"
                
        except Exception as e:
            print(f"  Error: {e}")
            
        # Test active-low
        print(f"\nTesting DO{bit} active-low:")
        try:
            controller.send_command(f"MO {axis}")
            controller.send_command("WT 100,0")  # Wait 100ms
            controller.send_command(f"CB {bit}")
            controller.send_command(f"SH {axis}")
            mo_status = controller.send_command(f"MG _MO{axis}")
            print(f"  MO{axis} status: {mo_status}")
            
            if mo_status.strip() == "0":
                print(f"  SUCCESS! DO{bit} active-low enables servo")
                return bit, "active-low"
                
        except Exception as e:
            print(f"  Error: {e}")
    
    print("\nNo DO bits enabled the servo. Check:")
    print("1. Drive enable wiring to DO pins")
    print("2. E-stop/safety chain closure")
    print("3. Drive power and ready signals")
    return None, None

if __name__ == "__main__":
    print("Manual Servo Enable Test")
    print("=======================")
    print("This script will test DO1..DO16 with both polarities")
    print("to find which bit enables your servo.")
    print()
    
    # You would need to initialize your controller here
    # For example:
    # from galil_combined import GalilController
    # controller = GalilController()
    # controller.connect("192.168.1.100")
    
    print("Note: Initialize your controller connection first, then uncomment the test call:")
    print("bit, polarity = test_servo_enable_bits(controller)")
    print("if bit:")
    print("    print(f'Use AMP_ENABLE_BITS = {{\"A\": ({bit}, \"{polarity}\")}}')")
    
    # Uncomment when ready to test:
    # bit, polarity = test_servo_enable_bits(controller)
    # if bit:
    #     print(f"\nFound working configuration:")
    #     print(f'AMP_ENABLE_BITS = {{"A": ({bit}, "{polarity}")}}')
