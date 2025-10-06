"""
Motor Preset Configurations for DMC-4143 + AMP-43540

This module contains preset motor configurations based on actual motor specifications
and successful setup results from GDK testing.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from motor_setup import MotorSpecs, CommutationMethod

@dataclass
class MotorPreset:
    """Motor preset configuration"""
    name: str
    description: str
    motor_specs: MotorSpecs
    commutation_method: CommutationMethod
    initialization_commands: List[str]
    verification_commands: List[str]
    notes: str

class MotorPresetManager:
    """Manager for motor preset configurations"""
    
    def __init__(self):
        """Initialize with predefined motor presets"""
        self.presets = self._create_presets()
    
    def _create_presets(self) -> Dict[str, MotorPreset]:
        """Create predefined motor presets"""
        presets = {}
        
        # Axis A - 20,000 counts/rev, 4 pole pairs (from GDK results)
        presets["axis_a_20k_4p"] = MotorPreset(
            name="Axis A - 20K Counts/Rev, 4 Pole Pairs",
            description="Standard brushless servo with 20,000 encoder counts per revolution and 4 pole pairs",
            motor_specs=MotorSpecs(
                encoder_counts_per_rev=20000,
                pole_pairs=4,
                has_index=True,
                has_halls=True
            ),
            commutation_method=CommutationMethod.BX,
            initialization_commands=[
                "MOA",           # Motor off
                "BAA",           # Enable sine-drive mode
                "DPA=0",         # Zero position
                "CEA=0",         # Normal encoder polarity
                "BMA=5000",      # BM = 20000/4 = 5000
                "BIA=-1",        # Use AMP-43540 dedicated hall inputs
                "OEA=1",         # Enable overtravel
                "ERA=_BMA",      # Set error limit >= BM
                "BX<1000>",      # Set hold time
                "BXA=3",         # Initialize with 3V
                "SHA"            # Enable servo
            ],
            verification_commands=[
                "TPA",           # Read position
                "MG _BMA",       # Verify BM setting
                "QH",            # Check hall status
                "MG _BDA",       # Read electrical angle
                "JGA=5000",      # Test motion
                "BGA",           # Begin motion
                "WT 500",        # Wait
                "ST",            # Stop motion
                "BN"             # Save settings
            ],
            notes="Based on successful GDK setup. Use BX method for minimal motion initialization."
        )
        
        # Axis A - Alternative with higher voltage for stubborn motors
        presets["axis_a_20k_4p_high_voltage"] = MotorPreset(
            name="Axis A - 20K Counts/Rev, 4 Pole Pairs (High Voltage)",
            description="Same as standard but with higher BX voltage for difficult initialization",
            motor_specs=MotorSpecs(
                encoder_counts_per_rev=20000,
                pole_pairs=4,
                has_index=True,
                has_halls=True
            ),
            commutation_method=CommutationMethod.BX,
            initialization_commands=[
                "MOA",           # Motor off
                "BAA",           # Enable sine-drive mode
                "DPA=0",         # Zero position
                "CEA=0",         # Normal encoder polarity
                "BMA=5000",      # BM = 20000/4 = 5000
                "BIA=-1",        # Use AMP-43540 dedicated hall inputs
                "OEA=1",         # Enable overtravel
                "ERA=_BMA",      # Set error limit >= BM
                "BX<2000>",      # Longer hold time
                "BXA=4",         # Higher voltage for difficult motors
                "SHA"            # Enable servo
            ],
            verification_commands=[
                "TPA",           # Read position
                "MG _BMA",       # Verify BM setting
                "QH",            # Check hall status
                "MG _BDA",       # Read electrical angle
                "JGA=5000",      # Test motion
                "BGA",           # Begin motion
                "WT 500",        # Wait
                "ST",            # Stop motion
                "BN"             # Save settings
            ],
            notes="Use this if standard BX method fails. Higher voltage and longer hold time."
        )
        
        # Axis A - BZ method (fallback)
        presets["axis_a_20k_4p_bz"] = MotorPreset(
            name="Axis A - 20K Counts/Rev, 4 Pole Pairs (BZ Method)",
            description="Same motor specs but using BZ method for more assertive initialization",
            motor_specs=MotorSpecs(
                encoder_counts_per_rev=20000,
                pole_pairs=4,
                has_index=True,
                has_halls=True
            ),
            commutation_method=CommutationMethod.BZ,
            initialization_commands=[
                "MOA",           # Motor off
                "BAA",           # Enable sine-drive mode
                "DPA=0",         # Zero position
                "CEA=0",         # Normal encoder polarity
                "BMA=5000",      # BM = 20000/4 = 5000
                "BIA=-1",        # Use AMP-43540 dedicated hall inputs
                "OEA=1",         # Enable overtravel
                "ERA=_BMA",      # Set error limit >= BM
                "BZ<2000>1000",  # Two-stage alignment
                "BZA=3",         # Drive to electrical zero
                "SHA"            # Enable servo
            ],
            verification_commands=[
                "TPA",           # Read position
                "MG _BMA",       # Verify BM setting
                "QH",            # Check hall status
                "MG _BDA",       # Read electrical angle
                "JGA=5000",      # Test motion
                "BGA",           # Begin motion
                "WT 500",        # Wait
                "ST",            # Stop motion
                "BN"             # Save settings
            ],
            notes="Fallback method if BX fails. More motion but more reliable."
        )
        
        # Generic template for other axes
        presets["generic_template"] = MotorPreset(
            name="Generic Motor Template",
            description="Template for motors with different specifications",
            motor_specs=MotorSpecs(
                encoder_counts_per_rev=10000,  # Default values
                pole_pairs=2,
                has_index=False,
                has_halls=True
            ),
            commutation_method=CommutationMethod.BX,
            initialization_commands=[
                "MOA",           # Motor off
                "BAA",           # Enable sine-drive mode
                "DPA=0",         # Zero position
                "CEA=0",         # Normal encoder polarity
                "BMA=5000",      # BM = counts/rev / pole_pairs
                "BIA=-1",        # Use AMP-43540 dedicated hall inputs
                "OEA=1",         # Enable overtravel
                "ERA=_BMA",      # Set error limit >= BM
                "BX<1000>",      # Set hold time
                "BXA=3",         # Initialize with 3V
                "SHA"            # Enable servo
            ],
            verification_commands=[
                "TPA",           # Read position
                "MG _BMA",       # Verify BM setting
                "QH",            # Check hall status
                "MG _BDA",       # Read electrical angle
                "JGA=5000",      # Test motion
                "BGA",           # Begin motion
                "WT 500",        # Wait
                "ST",            # Stop motion
                "BN"             # Save settings
            ],
            notes="Template for custom motor configurations. Adjust BM calculation as needed."
        )
        
        return presets
    
    def get_preset(self, preset_name: str) -> Optional[MotorPreset]:
        """Get a specific motor preset by name"""
        return self.presets.get(preset_name)
    
    def get_all_presets(self) -> Dict[str, MotorPreset]:
        """Get all available presets"""
        return self.presets.copy()
    
    def get_preset_names(self) -> List[str]:
        """Get list of all preset names"""
        return list(self.presets.keys())
    
    def create_custom_preset(self, name: str, description: str, 
                           encoder_counts: int, pole_pairs: int,
                           has_index: bool = True, has_halls: bool = True,
                           commutation_method: CommutationMethod = CommutationMethod.BX) -> MotorPreset:
        """Create a custom motor preset"""
        bm_value = encoder_counts / pole_pairs
        
        preset = MotorPreset(
            name=name,
            description=description,
            motor_specs=MotorSpecs(
                encoder_counts_per_rev=encoder_counts,
                pole_pairs=pole_pairs,
                has_index=has_index,
                has_halls=has_halls
            ),
            commutation_method=commutation_method,
            initialization_commands=[
                "MOA",           # Motor off
                "BAA",           # Enable sine-drive mode
                "DPA=0",         # Zero position
                "CEA=0",         # Normal encoder polarity
                f"BMA={bm_value}",  # Calculated BM
                "BIA=-1",        # Use AMP-43540 dedicated hall inputs
                "OEA=1",         # Enable overtravel
                "ERA=_BMA",      # Set error limit >= BM
                "BX<1000>",      # Set hold time
                "BXA=3",         # Initialize with 3V
                "SHA"            # Enable servo
            ],
            verification_commands=[
                "TPA",           # Read position
                "MG _BMA",       # Verify BM setting
                "QH A",          # Check hall status
                "MG _BDA",       # Read electrical angle
                "JGA=5000",      # Test motion
                "BGA",           # Begin motion
                "WT 500",        # Wait
                "STA",           # Stop motion
                "BN"             # Save settings
            ],
            notes=f"Custom preset: {encoder_counts} counts/rev, {pole_pairs} pole pairs, BM={bm_value}"
        )
        
        self.presets[name] = preset
        return preset
    
    def get_preset_for_axis(self, axis: str, motor_type: str = "standard") -> Optional[MotorPreset]:
        """Get appropriate preset for specific axis and motor type"""
        if motor_type == "standard":
            return self.get_preset("axis_a_20k_4p")
        elif motor_type == "high_voltage":
            return self.get_preset("axis_a_20k_4p_high_voltage")
        elif motor_type == "bz_method":
            return self.get_preset("axis_a_20k_4p_bz")
        else:
            return self.get_preset("generic_template")
    
    def print_preset_summary(self, preset_name: str):
        """Print a summary of a motor preset"""
        preset = self.get_preset(preset_name)
        if not preset:
            print(f"Preset '{preset_name}' not found")
            return
        
        print(f"\n=== {preset.name} ===")
        print(f"Description: {preset.description}")
        print(f"Encoder Counts/Rev: {preset.motor_specs.encoder_counts_per_rev}")
        print(f"Pole Pairs: {preset.motor_specs.pole_pairs}")
        print(f"Has Index: {preset.motor_specs.has_index}")
        print(f"Has Halls: {preset.motor_specs.has_halls}")
        print(f"Commutation Method: {preset.commutation_method.value}")
        print(f"Notes: {preset.notes}")
        
        print("\nInitialization Commands:")
        for i, cmd in enumerate(preset.initialization_commands, 1):
            print(f"  {i:2d}. {cmd}")
        
        print("\nVerification Commands:")
        for i, cmd in enumerate(preset.verification_commands, 1):
            print(f"  {i:2d}. {cmd}")

# Global preset manager instance
preset_manager = MotorPresetManager()

# Convenience functions
def get_axis_a_preset() -> MotorPreset:
    """Get the standard Axis A preset (20K counts/rev, 4 pole pairs)"""
    return preset_manager.get_preset("axis_a_20k_4p")

def get_axis_a_high_voltage_preset() -> MotorPreset:
    """Get the high voltage Axis A preset"""
    return preset_manager.get_preset("axis_a_20k_4p_high_voltage")

def get_axis_a_bz_preset() -> MotorPreset:
    """Get the BZ method Axis A preset"""
    return preset_manager.get_preset("axis_a_20k_4p_bz")

def list_all_presets():
    """List all available presets"""
    print("Available Motor Presets:")
    print("=" * 50)
    for name, preset in preset_manager.get_all_presets().items():
        print(f"{name}: {preset.description}")
