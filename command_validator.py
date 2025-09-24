"""
Command Validator for DMC-4103 Controller

Validates motor setup commands against the DMC-4103 command reference.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import re

@dataclass
class CommandValidation:
    valid: bool
    command: str
    description: str
    error_message: Optional[str] = None
    warning_message: Optional[str] = None

class DMC4103CommandValidator:
    def __init__(self):
        self.valid_commands = self._load_command_reference()
        self.axis_commands = self._load_axis_commands()
        self.parameter_commands = self._load_parameter_commands()

    def _load_command_reference(self) -> Dict[str, Dict]:
        return {
            # Motion / servo
            "MO": {"description": "Motor Off", "parameters": ["axis"]},
            "SH": {"description": "Servo Here (Enable)", "parameters": ["axis"]},
            "ST": {"description": "Stop Motion", "parameters": ["axis"]},
            "BG": {"description": "Begin Motion", "parameters": ["axis"]},
            "AM": {"description": "After Motion", "parameters": ["axis"]},

            # Positioning
            "TP": {"description": "Tell Position", "parameters": ["axis"]},
            "DP": {"description": "Define Position", "parameters": ["axis", "value"]},
            "PA": {"description": "Position Absolute", "parameters": ["axis", "value"]},
            "PR": {"description": "Position Relative", "parameters": ["axis", "value"]},
            "JG": {"description": "Jog", "parameters": ["axis", "value"]},
            "FI": {"description": "Find Index", "parameters": ["axis"]},

            # Brushless
            "BA": {"description": "Brushless Amplifier", "parameters": ["axis"]},
            "BM": {"description": "Brushless Modulo", "parameters": ["axis", "value"]},
            "BX": {"description": "Brushless eXchange", "parameters": ["axis", "value"]},
            "BZ": {"description": "Brushless Zero", "parameters": ["axis", "value"]},
            "BC": {"description": "Brushless Calibrate", "parameters": ["axis"]},
            "BI": {"description": "Brushless Input", "parameters": ["axis", "value"]},
            "QH": {"description": "Query Hall", "parameters": []},

            # Encoder / latch
            "CE": {"description": "Count Enable", "parameters": ["axis", "value"]},
            "AL": {"description": "After Latch", "parameters": ["axis"]},
            "RL": {"description": "Read Latch", "parameters": ["axis"]},

            # Safety / limits
            "OE": {"description": "Off on Error", "parameters": ["axis", "value"]},
            "ER": {"description": "Error Limit", "parameters": ["axis", "value"]},

            # Tuning / servo parameters (axis=value)
            "TL": {"description": "Torque Limit", "parameters": ["axis", "value"]},
            "TK": {"description": "Torque Bias", "parameters": ["axis", "value"]},
            "OF": {"description": "DAC Offset", "parameters": ["axis", "value"]},
            "KP": {"description": "Proportional Gain", "parameters": ["axis", "value"]},
            "KI": {"description": "Integral Gain", "parameters": ["axis", "value"]},
            "KD": {"description": "Derivative Gain", "parameters": ["axis", "value"]},
            "AC": {"description": "Acceleration", "parameters": ["axis", "value"]},
            "DC": {"description": "Deceleration", "parameters": ["axis", "value"]},
            "SP": {"description": "Speed", "parameters": ["axis", "value"]},

            # System / diagnostics / misc
            "BN": {"description": "Burn (save parameters)", "parameters": []},
            "RS": {"description": "Reset", "parameters": []},
            "AB": {"description": "Abort", "parameters": []},
            "AZ": {"description": "Amplifier Fault Reset", "parameters": []},
            "MG": {"description": "Message", "parameters": ["variable"]},
            "WT": {"description": "Wait", "parameters": ["time"]},
            "MT": {"description": "Motor Type", "parameters": ["list"]},
            "TE": {"description": "Tell Error Code", "parameters": []},
            # TC optionally accepts a mode digit (e.g., "TC1"); we accept both "TC" and "TC 1"/"TC1"
            "TC": {"description": "Tell Error Text", "parameters": ["optional_mode"]},
        }

    def _load_axis_commands(self) -> List[str]:
        return [
            "MO","SH","ST","BG","AM","TP","DP","PA","PR","JG","FI",
            "BA","BM","BX","BZ","BC","BI","CE","AL","RL","OE","ER",
            "TL","TK","OF","KP","KI","KD","AC","DC","SP"
        ]

    def _load_parameter_commands(self) -> List[str]:
        return [
            "DP","PA","PR","JG","BM","BX","BZ","BI","CE","ER","WT",
            "TL","TK","OF","KP","KI","KD","AC","DC","SP","MT","TC"
        ]

    _NUM = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"

    def validate_command(self, command: str) -> CommandValidation:
        try:
            raw = command.strip()

            # Parse head/value, preserving bracket-tail like "<200>100"
            if "<" in raw and ">" in raw:
                lt = raw.find("<"); gt = raw.find(">", lt + 1)
                cmd_part = raw[:lt].strip()
                right_tail = raw[gt + 1:].strip()
                value = raw[lt:gt + 1] + (right_tail if right_tail else "")
            elif "=" in raw:
                cmd_part, value = raw.split("=", 1); cmd_part = cmd_part.strip(); value = value.strip()
            elif " " in raw:
                cmd_part, value = raw.split(" ", 1); cmd_part = cmd_part.strip(); value = value.strip()
            else:
                cmd_part, value = raw, None

            # Longest-prefix match for base command
            candidates = [c for c in self.valid_commands if cmd_part.startswith(c)]
            base_cmd = max(candidates, key=len) if candidates else None
            if not base_cmd:
                return CommandValidation(False, raw, "Unknown command",
                                         f"Command '{cmd_part}' not found in DMC-4103 reference")

            # Extract axis or (for non-axis commands) inline value after the base
            axis = None
            remainder = cmd_part[len(base_cmd):].strip()
            if base_cmd in self.axis_commands:
                if remainder:
                    axis = remainder  # e.g., "BZA" -> "A"
                elif value and value in {"A","B","C","D"}:
                    axis = value      # e.g., "BA A"
            else:
                # Non-axis commands may have inline numeric mode, e.g., "TC1"
                if remainder and value is None:
                    value = remainder

            # Axis validation (skip for BX/BZ hold-time only form)
            if base_cmd in self.axis_commands:
                if base_cmd in ("BX","BZ") and value and value.startswith("<"):
                    pass
                else:
                    if axis not in {"A","B","C","D"}:
                        return CommandValidation(False, raw, self.valid_commands[base_cmd]["description"],
                                                 f"Command '{base_cmd}' requires valid axis (A, B, C, D), got '{axis}'")

            # Parameter validation
            if base_cmd in self.parameter_commands:
                if base_cmd in ("BX","BZ"):
                    ok, err = self._validate_bx_bz(value)
                elif base_cmd == "BI":
                    ok, err = self._validate_bi(value)
                elif base_cmd == "CE":
                    ok, err = self._validate_ce(value)
                elif base_cmd == "OE":
                    ok, err = self._validate_oe(value)
                elif base_cmd == "ER":
                    ok, err = self._validate_er(value)
                elif base_cmd == "WT":
                    ok, err = self._validate_positive_number(value, "WT")
                elif base_cmd == "MT":
                    ok, err = self._validate_mt_list(value)
                elif base_cmd == "TC":
                    ok, err = self._validate_tc_mode_optional(value)
                else:
                    ok, err = self._validate_generic_numeric_required(value, base_cmd)
                if not ok:
                    return CommandValidation(False, raw, self.valid_commands[base_cmd]["description"], err)

            # Warnings / soft bounds
            warning = self._check_warnings(base_cmd, axis, value)
            return CommandValidation(True, raw, self.valid_commands[base_cmd]["description"],
                                     warning_message=warning)

        except Exception as e:
            return CommandValidation(False, command, "Parse error", f"Failed to parse command: {e}")

    # ----------- helpers -----------

    def _validate_generic_numeric_required(self, value: Optional[str], base_cmd: str) -> Tuple[bool, Optional[str]]:
        if value is None:
            return False, f"Command '{base_cmd}' requires a parameter value"
        try:
            float(value)
            return True, None
        except Exception:
            return False, f"Invalid numeric value: {value}"

    def _validate_bx_bz(self, value: Optional[str]) -> Tuple[bool, Optional[str]]:
        if value is None:
            return False, "BX/BZ requires a parameter (axis+value, numeric value, or <p>[o])"
        if value.startswith("<"):
            # Accept "<p>" or "<p>o"
            m = re.match(rf"^<\s*{self._NUM}\s*>\s*(?:{self._NUM})?$", value)
            return (True, None) if m else (False, f"Invalid BX/BZ bracket form: {value}")
        try:
            float(value)
            return True, None
        except Exception:
            return False, f"Invalid BX/BZ numeric value: {value}"

    def _validate_bi(self, value: Optional[str]) -> Tuple[bool, Optional[str]]:
        if value is None:
            return False, "BI requires -1 or integer 1-8"
        if value == "-1":
            return True, None
        try:
            iv = int(value)
            return (True, None) if 1 <= iv <= 8 else (False, "BI parameter must be -1 or input number 1-8")
        except Exception:
            return False, "BI parameter must be -1 or integer 1-8"

    def _validate_ce(self, value: Optional[str]) -> Tuple[bool, Optional[str]]:
        return (True, None) if value in ("0","2") else (False, "CE parameter must be 0 (normal) or 2 (reversed)")

    def _validate_oe(self, value: Optional[str]) -> Tuple[bool, Optional[str]]:
        return (True, None) if value in ("0","1") else (False, "OE parameter must be 0 (disabled) or 1 (enabled)")

    def _validate_er(self, value: Optional[str]) -> Tuple[bool, Optional[str]]:
        if value is None:
            return False, "ER requires a numeric value or a variable reference (e.g., _BMA)"
        if value.startswith("_"):
            return True, None
        try:
            float(value)
            return True, None
        except Exception:
            return False, f"Invalid ER value: {value}"

    def _validate_positive_number(self, value: Optional[str], name: str) -> Tuple[bool, Optional[str]]:
        try:
            v = float(value)
            return (True, None) if v > 0 else (False, f"{name} must be positive")
        except Exception:
            return False, f"Invalid numeric value for {name}: {value}"

    def _validate_mt_list(self, value: Optional[str]) -> Tuple[bool, Optional[str]]:
        if value is None:
            return False, "MT requires a list like '1,1,1,1'"
        parts = [p.strip() for p in value.split(",")]
        if not parts:
            return False, "MT requires comma-separated values"
        for p in parts:
            if not re.fullmatch(r"\d+", p):
                return False, f"MT contains non-integer token: {p}"
        return True, None

    def _validate_tc_mode_optional(self, value: Optional[str]) -> Tuple[bool, Optional[str]]:
        # Accept: "TC" (no mode), "TC 1", or "TC1" (we already mapped inline remainder to value)
        if value is None or value == "":
            return True, None
        # allow small integer mode selector
        if re.fullmatch(r"\d+", value):
            return True, None
        return False, f"Invalid TC mode '{value}' (use e.g. 'TC', 'TC 1' or 'TC1')"

    # ----------- warnings / soft bounds -----------

    def _check_warnings(self, command: str, axis: Optional[str], value: Optional[str]) -> Optional[str]:
        warnings = []

        def _float_ok(x: Optional[str]) -> Optional[float]:
            try:
                return float(x) if x is not None else None
            except Exception:
                return None

        if command in ("BX","BZ") and value and not value.startswith("<"):
            v = _float_ok(value)
            if v is not None:
                if abs(v) < 2:
                    warnings.append(f"{command} voltage may be low; -3 is typical for alignment")
                elif abs(v) > 5:
                    warnings.append(f"{command} voltage may be high; verify driver limits")

        if command == "BM" and value:
            v = _float_ok(value)
            if v is not None:
                if v < 100:
                    warnings.append("BM value seems low; verify encoder counts and pole pairs")
                elif v > 50000:
                    warnings.append("BM value seems high; verify encoder counts and pole pairs")

        if command == "TL" and value:
            v = _float_ok(value)
            if v is not None:
                if v < 0:
                    warnings.append("TL (torque limit) is negative; set ≥ 0")
                elif v > 10:
                    warnings.append("TL exceeds 10; most AMP/DAC ranges are ±10V")

        if command in ("TK","OF") and value:
            v = _float_ok(value)
            if v is not None and abs(v) > 10:
                warnings.append(f"{command} magnitude >10; typical DAC range is ±10V")

        if command in ("KP","KI","KD") and value:
            v = _float_ok(value)
            if v is not None and v < 0:
                warnings.append(f"{command} is negative; gains are usually ≥ 0")

        if command in ("AC","DC","SP") and value:
            v = _float_ok(value)
            if v is not None and v < 0:
                warnings.append(f"{command} is negative; expected ≥ 0")

        return "; ".join(warnings) if warnings else None

    # ----------- sequence / help -----------

    def validate_motor_setup_sequence(self, commands: List[str]) -> List[CommandValidation]:
        return [self.validate_command(c) for c in commands]

    def get_command_help(self, command: str) -> str:
        if command in self.valid_commands:
            d = self.valid_commands[command]
            help_text = f"{command}: {d['description']}\n"
            if "parameters" in d:
                help_text += f"Parameters: {', '.join(d['parameters'])}\n"
            examples = {
                "MO": "MOA",
                "SH": "SHA",
                "BM": "BMA=16000",
                "BX": "BXA=-3   |   BX<200>100",
                "BZ": "BZA=-3   |   BZ<200>100",
                "CE": "CEA=0 (normal), CEA=2 (reversed)",
                "FI": "FIA",
                "TL": "TLA=8.0",
                "TK": "TKA=0",
                "OF": "OFA=0",
                "KP": "KPA=10.0",
                "KI": "KIA=0.1",
                "KD": "KDA=50.0",
                "AC": "ACA=200000",
                "DC": "DCA=200000",
                "SP": "SPA=20000",
                "MT": "MT 1,1,1,1",
                "TE": "TE",
                "TC": "TC   |   TC 1   |   TC1",
            }
            if command in examples:
                help_text += "Example: " + examples[command] + "\n"
            return help_text
        return f"Unknown command: {command}"

    def get_all_commands(self) -> List[str]:
        return list(self.valid_commands.keys())

    def get_axis_commands(self) -> List[str]:
        return self.axis_commands.copy()

    def get_parameter_commands(self) -> List[str]:
        return self.parameter_commands.copy()