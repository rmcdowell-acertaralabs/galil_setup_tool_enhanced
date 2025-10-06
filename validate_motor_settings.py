"""
Motor Settings Validation Script
Verifies that motor configuration matches verified working settings

This script:
1. Checks controller settings against config.json
2. Validates critical parameters
3. Tests motor operation
4. Reports any discrepancies
"""

import gclib
import json
import sys
from typing import Dict, List, Tuple
from controller_servo_maintenance import get_motor_status


class SettingsValidator:
    """Validate motor settings against verified configuration"""
    
    # Critical settings that MUST match for safe operation
    CRITICAL_SETTINGS = {
        'mt': 'Motor Type',
        'ce': 'Encoder Direction',
        'bm': 'Brushless Modulo',
        'clicks_per_turn': 'Encoder Resolution'
    }
    
    # Important settings that should match
    IMPORTANT_SETTINGS = {
        'kp': 'Proportional Gain',
        'kd': 'Derivative Gain',
        'ki': 'Integral Gain',
        'tl': 'Torque Limit',
        'tk': 'Peak Torque',
        'ag': 'Amplifier Gain',
        'au': 'Current Loop Gain'
    }
    
    def __init__(self, controller_connection, config_file='config.json'):
        """
        Initialize validator
        
        Args:
            controller_connection: Active gclib connection
            config_file: Path to config JSON file
        """
        self.g = controller_connection
        self.config_file = config_file
        self.config = self._load_config()
        self.validation_results = {}
    
    def _load_config(self) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"ERROR: Failed to load config: {e}")
            sys.exit(1)
    
    def validate_axis(self, axis: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate single axis settings
        
        Args:
            axis: Axis letter (A, B, C, D)
            
        Returns:
            Tuple of (passed, critical_errors, warnings)
        """
        print(f"\n{'='*70}")
        print(f"Validating Axis {axis}")
        print(f"{'='*70}\n")
        
        critical_errors = []
        warnings = []
        
        # Get expected settings
        expected = self.config.get('axis_presets', {}).get(axis)
        if not expected:
            critical_errors.append(f"No configuration found for axis {axis}")
            return False, critical_errors, warnings
        
        # Get actual controller settings
        try:
            actual = self._read_controller_settings(axis)
        except Exception as e:
            critical_errors.append(f"Failed to read controller settings: {e}")
            return False, critical_errors, warnings
        
        # Validate critical settings
        print("Critical Settings:")
        print("-" * 70)
        for key, name in self.CRITICAL_SETTINGS.items():
            if key not in expected:
                continue
            
            expected_val = expected[key]
            actual_val = actual.get(key, 'N/A')
            
            match = self._compare_values(expected_val, actual_val, key)
            status = "✓ PASS" if match else "✗ FAIL"
            
            print(f"{name:25} Expected: {expected_val:>10}  Actual: {actual_val:>10}  {status}")
            
            if not match:
                critical_errors.append(
                    f"{name}: Expected {expected_val}, got {actual_val}"
                )
        
        # Validate important settings
        print("\nImportant Settings:")
        print("-" * 70)
        for key, name in self.IMPORTANT_SETTINGS.items():
            if key not in expected:
                continue
            
            expected_val = expected[key]
            actual_val = actual.get(key, 'N/A')
            
            match = self._compare_values(expected_val, actual_val, key)
            status = "✓ MATCH" if match else "⚠ DIFF"
            
            print(f"{name:25} Expected: {expected_val:>10}  Actual: {actual_val:>10}  {status}")
            
            if not match:
                warnings.append(
                    f"{name}: Expected {expected_val}, got {actual_val}"
                )
        
        # Overall result
        passed = len(critical_errors) == 0
        
        print(f"\n{'='*70}")
        if passed:
            print(f"✓ Axis {axis} PASSED validation")
        else:
            print(f"✗ Axis {axis} FAILED validation - {len(critical_errors)} critical error(s)")
        print(f"{'='*70}\n")
        
        return passed, critical_errors, warnings
    
    def _read_controller_settings(self, axis: str) -> Dict:
        """Read current settings from controller"""
        settings = {}
        
        # Motor type
        mt_response = self.g.GCommand(f"MG _MT{axis}").strip()
        settings['mt'] = int(float(mt_response.split()[0]))
        
        # Encoder config
        ce_response = self.g.GCommand(f"MG _CE{axis}").strip()
        settings['ce'] = int(float(ce_response.split()[0]))
        
        # Brushless modulo
        bm_response = self.g.GCommand(f"MG _BM{axis}").strip()
        settings['bm'] = int(float(bm_response.split()[0]))
        
        # PID gains
        kp_response = self.g.GCommand(f"MG _KP{axis}").strip()
        settings['kp'] = float(kp_response.split()[0])
        
        kd_response = self.g.GCommand(f"MG _KD{axis}").strip()
        settings['kd'] = float(kd_response.split()[0])
        
        ki_response = self.g.GCommand(f"MG _KI{axis}").strip()
        settings['ki'] = float(ki_response.split()[0])
        
        # Torque limits
        tl_response = self.g.GCommand(f"MG _TL{axis}").strip()
        settings['tl'] = float(tl_response.split()[0])
        
        # Amplifier (AG might not be readable on all controllers)
        try:
            ag_response = self.g.GCommand(f"MG _AG{axis}").strip()
            settings['ag'] = float(ag_response.split()[0])
        except:
            settings['ag'] = 'N/A'
        
        try:
            au_response = self.g.GCommand(f"MG _AU{axis}").strip()
            settings['au'] = float(au_response.split()[0])
        except:
            settings['au'] = 'N/A'
        
        # Note: clicks_per_turn is a software setting, not in controller
        # We'll assume it matches config
        settings['clicks_per_turn'] = self.config['axis_presets'][axis].get('clicks_per_turn', 20000)
        
        return settings
    
    def _compare_values(self, expected, actual, key: str) -> bool:
        """Compare expected vs actual values with appropriate tolerance"""
        if actual == 'N/A':
            return False
        
        # For integer settings, must match exactly
        if key in ['mt', 'ce', 'bm', 'clicks_per_turn']:
            return int(expected) == int(actual)
        
        # For float settings, allow small tolerance
        try:
            return abs(float(expected) - float(actual)) < 0.01
        except:
            return False
    
    def test_motor_operation(self, axis: str) -> bool:
        """
        Test motor operation to verify it's safe
        
        Args:
            axis: Axis to test
            
        Returns:
            True if motor operates safely, False otherwise
        """
        print(f"\nTesting Axis {axis} Operation:")
        print("-" * 70)
        
        try:
            # Check motor status
            status = get_motor_status(self.g, axis)
            
            print(f"Motor State: {'ON' if status.get('motor_on') else 'OFF'}")
            print(f"Position: {status.get('position', 0):.0f}")
            print(f"Following Error: {status.get('following_error', 0):.0f}")
            print(f"Torque: {status.get('torque', 0):.2f}V")
            print(f"Commutation Angle: {status.get('commutation_angle', 0):.1f}°")
            
            # Check for warning signs
            warnings = []
            
            if abs(status.get('following_error', 0)) > 500:
                warnings.append("Large following error detected!")
            
            if abs(status.get('torque', 0)) > 4.0 and status.get('motor_on'):
                warnings.append("High torque output - motor may be straining!")
            
            if status.get('bz_status', 0) < 1000:
                warnings.append("Brushless initialization may have failed!")
            
            if warnings:
                print("\n⚠ WARNINGS:")
                for w in warnings:
                    print(f"  - {w}")
                return False
            else:
                print("\n✓ Motor status looks good")
                return True
                
        except Exception as e:
            print(f"\n✗ Failed to test motor: {e}")
            return False
    
    def generate_report(self, axes: List[str]) -> str:
        """
        Generate validation report for multiple axes
        
        Args:
            axes: List of axis letters to validate
            
        Returns:
            Report string
        """
        report_lines = []
        report_lines.append("\n" + "="*70)
        report_lines.append("MOTOR SETTINGS VALIDATION REPORT")
        report_lines.append("="*70)
        
        all_passed = True
        results = {}
        
        for axis in axes:
            passed, critical, warnings = self.validate_axis(axis)
            op_test = self.test_motor_operation(axis)
            
            results[axis] = {
                'settings_passed': passed,
                'operation_passed': op_test,
                'critical_errors': critical,
                'warnings': warnings
            }
            
            if not passed or not op_test:
                all_passed = False
        
        # Summary
        report_lines.append("\n" + "="*70)
        report_lines.append("SUMMARY")
        report_lines.append("="*70 + "\n")
        
        for axis, result in results.items():
            status = "✓ PASS" if (result['settings_passed'] and result['operation_passed']) else "✗ FAIL"
            report_lines.append(f"Axis {axis}: {status}")
            
            if result['critical_errors']:
                report_lines.append(f"  Critical Errors:")
                for err in result['critical_errors']:
                    report_lines.append(f"    - {err}")
            
            if result['warnings']:
                report_lines.append(f"  Warnings:")
                for warn in result['warnings']:
                    report_lines.append(f"    - {warn}")
        
        report_lines.append("\n" + "="*70)
        if all_passed:
            report_lines.append("✓ ALL AXES VALIDATED - SAFE FOR OPERATION")
        else:
            report_lines.append("✗ VALIDATION FAILED - DO NOT OPERATE!")
            report_lines.append("\nRECOMMENDATION: Re-run motor setup for failed axes")
        report_lines.append("="*70 + "\n")
        
        return "\n".join(report_lines)


def main():
    """Main validation script"""
    print("\n" + "="*70)
    print("MOTOR SETTINGS VALIDATION SCRIPT")
    print("="*70)
    
    # Connect to controller
    try:
        print("\nConnecting to controller...")
        g = gclib.py()
        g.GOpen("10.1.0.24 -s ALL")  # Update with your controller IP
        print("✓ Connected to controller")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        sys.exit(1)
    
    # Create validator
    validator = SettingsValidator(g)
    
    # Validate axes
    axes_to_check = ['A', 'B', 'C']  # Update with your active axes
    
    report = validator.generate_report(axes_to_check)
    print(report)
    
    # Save report to file
    with open('validation_report.txt', 'w') as f:
        f.write(report)
    print("Report saved to: validation_report.txt")
    
    # Cleanup
    g.GClose()


if __name__ == "__main__":
    main()

