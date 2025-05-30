# Copyright 2014-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from platformio.managers.platform import PlatformBase

class Hc32f46xPlatform(PlatformBase):
    def configure_default_packages(self, variables, targets):
        if variables.get("board"):
            upload_protocol = variables.get("upload_protocol", self.board_config(variables.get("board")).get("upload.protocol", ""))
            if upload_protocol == "cmsis-dap":
                self.packages["tool-pyocd"]["type"] = "uploader"
            elif upload_protocol == "jlink":
                self.packages["tool-jlink"]["type"] = "uploader"
        
        return super().configure_default_packages(variables, targets)

    def get_boards(self, id_=None):
        result = PlatformBase.get_boards(self, id_)
        if not result:
            return result
        
        if id_:
            return self._add_default_debug_tools(result)
        else:
            for key, value in result.items():
                result[key] = self._add_default_debug_tools(result[key])
        
        return result

    def _add_default_debug_tools(self, board):
        debug = board.manifest.get("debug", {})
        if "tools" not in debug:
            debug["tools"] = {}

        # add configurations for pyOCD based debugging probes
        # supported probes see https://pyocd.io/docs/debug_probes.html
        # Note: recent stlink versions block non-ST parts and won't work
        for interface in ("cmsis-dap", "jlink", "stlink"):
            # skip if the tool is already defined
            if interface in debug["tools"]:
                continue

            # get target script from board manifest
            pyocd_target = debug.get("pyocd_target")
            assert pyocd_target, (
                f"Missed target configuration for {board.id}")
            
            # create pyOCD server arguments
            server_args = [
                "-m", "pyocd",
                "gdbserver",
                "--no-wait",
                "--target", pyocd_target,
            ]
            server_args.extend(debug.get("pyocd_extra_args", []))
            
            # assign the tool configuration
            if interface == "jlink":
                # J-Link specific configuration
                jlink_device = debug.get("jlink_device", "HC32F460")
                debug["tools"][interface] = {
                    "server": {
                        "package": "tool-jlink",
                        "executable": "JLinkGDBServer",
                        "arguments": [
                            "-singlerun",
                            "-if", "swd",
                            "-select", "usb",
                            "-device", jlink_device,
                            "-port", "3333",
                            "-speed", "4000",
                        ],
                    },
                    "upload_protocol": "jlink",
                    "onboard": debug.get("onboard_tools", []) and interface in debug.get("onboard_tools", []),
                    "port": ":3333",
                }
            else:
                # pyOCD based configuration
                debug["tools"][interface] = {
                    "server": {
                        "package": "tool-pyocd",
                        "executable": "$PYTHONEXE",
                        "arguments": server_args,
                        "ready_pattern": "GDB server started on port 3333",
                    },
                    "port": ":3333",
                }

        board.manifest["debug"] = debug
        return board
