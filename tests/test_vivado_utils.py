"""
Tests for src/vivado_utils.py
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add src to path for imports
from src.vivado_handling import (
    find_vivado_installation,
    get_vivado_executable,
    get_vivado_version,
    run_vivado_command,
)

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestVivadoDetection:
    """Test Vivado detection functionality."""

    @patch("shutil.which")
    def test_find_vivado_in_path(self, mock_which):
        """Test finding Vivado in PATH."""
        # Mock Vivado in PATH
        mock_which.return_value = "/usr/bin/vivado"

        with patch("subprocess.run") as mock_run:
            # Mock version command output
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.stdout = "Vivado v2023.1 (64-bit)"
            mock_run.return_value = mock_process

            # Call the function
            result = find_vivado_installation()

            # Verify results
            assert result is not None
            assert result["executable"] == "/usr/bin/vivado"
            assert result["version"] == "2023.1"
            assert result["bin_path"] == "/usr/bin"

            # Verify the subprocess call
            mock_run.assert_called_once()

    @patch("shutil.which")
    @patch("os.path.exists")
    @patch("os.path.isdir")
    @patch("os.listdir")
    def test_find_vivado_in_common_locations(
        self, mock_listdir, mock_isdir, mock_exists, mock_which
    ):
        """Test finding Vivado in common installation locations."""
        # Mock Vivado not in PATH
        mock_which.return_value = None

        # Mock directory existence
        mock_exists.side_effect = lambda path: "/opt/Xilinx/Vivado" in path
        mock_isdir.side_effect = lambda path: "/opt/Xilinx/Vivado" in path

        # Mock directory listing
        mock_listdir.return_value = ["2021.2", "2022.1", "2023.1"]

        # Call the function
        with patch("os.path.isfile", return_value=True):
            with patch("subprocess.run") as mock_run:
                # Mock version command output
                mock_process = Mock()
                mock_process.returncode = 0
                mock_process.stdout = ""
                mock_run.return_value = mock_process

                result = find_vivado_installation()

                # Verify results
                assert result is not None
                assert "2023.1" in result["path"]
                assert result["version"] == "2023.1"

    @patch("shutil.which")
    @patch("os.path.exists")
    @patch("os.environ")
    def test_find_vivado_from_environment_variable(
        self, mock_environ, mock_exists, mock_which
    ):
        """Test finding Vivado using XILINX_VIVADO environment variable."""
        # Mock Vivado not in PATH
        mock_which.return_value = None

        # Mock environment variable
        mock_environ.get.side_effect = lambda key, default=None: (
            "/opt/Xilinx/Vivado/2023.1" if key == "XILINX_VIVADO" else default
        )

        # Mock file existence
        def mock_exists_side_effect(path):
            return (
                "/opt/Xilinx/Vivado/2023.1" in path
                or "/opt/Xilinx/Vivado/2023.1/bin" in path
                or "/opt/Xilinx/Vivado/2023.1/bin/vivado" in path
            )

        mock_exists.side_effect = mock_exists_side_effect

        # Call the function
        with patch("os.path.isdir", return_value=True):
            with patch("os.path.isfile", return_value=True):
                result = find_vivado_installation()

                # Verify results
                assert result is not None
                assert result["path"] == "/opt/Xilinx/Vivado/2023.1"
                assert result["version"] == "2023.1"

    @patch("shutil.which")
    @patch("os.path.exists")
    def test_vivado_not_found(self, mock_exists, mock_which):
        """Test behavior when Vivado is not found."""
        # Mock Vivado not in PATH
        mock_which.return_value = None

        # Mock directory non-existence
        mock_exists.return_value = False

        # Mock environment variable not set
        with patch("os.environ.get", return_value=None):
            result = find_vivado_installation()

            # Verify results
            assert result is None

    def test_get_vivado_version_from_output(self):
        """Test extracting Vivado version from command output."""
        # Test with standard output format
        output = """
        ****** Vivado v2023.1 (64-bit)
        **** SW Build 3865809 on Sun May 07 15:05:29 MDT 2023
        **** IP Build 3864474 on Sun May 07 20:36:21 MDT 2023
        """
        version = get_vivado_version("/dummy/path")

        # Since we can't actually run Vivado, we'll just check the function
        # logic
        with patch("subprocess.run") as mock_run:
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.stdout = output
            mock_run.return_value = mock_process

            version = get_vivado_version("/dummy/path")
            assert version == "2023.1"

        # Test with non-standard output
        with patch("subprocess.run") as mock_run:
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.stdout = "Some other output without version"
            mock_run.return_value = mock_process

            # Should extract from path as fallback
            version = get_vivado_version("/opt/Xilinx/Vivado/2022.2/bin/vivado")
            assert version == "2022.2"

    @patch("src.vivado_handling.vivado_utils.find_vivado_installation")
    def test_run_vivado_command(self, mock_find_vivado):
        """Test running Vivado commands."""
        # Mock Vivado installation
        mock_find_vivado.return_value = {
            "executable": "/opt/Xilinx/Vivado/2023.1/bin/vivado",
            "version": "2023.1",
            "path": "/opt/Xilinx/Vivado/2023.1",
            "bin_path": "/opt/Xilinx/Vivado/2023.1/bin",
        }

        # Test running a command
        with patch("subprocess.run") as mock_run:
            mock_process = Mock()
            mock_process.returncode = 0
            mock_run.return_value = mock_process

            run_vivado_command("-mode batch")

            # Verify the subprocess call
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert args[0][0] == "/opt/Xilinx/Vivado/2023.1/bin/vivado"
            assert args[0][1] == "-mode"
            assert args[0][2] == "batch"

    @patch("src.vivado_handling.vivado_utils.find_vivado_installation")
    def test_run_vivado_command_with_tcl(self, mock_find_vivado):
        """Test running Vivado commands with TCL file."""
        # Mock Vivado installation
        mock_find_vivado.return_value = {
            "executable": "/opt/Xilinx/Vivado/2023.1/bin/vivado",
            "version": "2023.1",
            "path": "/opt/Xilinx/Vivado/2023.1",
            "bin_path": "/opt/Xilinx/Vivado/2023.1/bin",
        }

        # Test running a command with TCL file
        with patch("subprocess.run") as mock_run:
            mock_process = Mock()
            mock_process.returncode = 0
            mock_run.return_value = mock_process

            run_vivado_command("-mode batch", tcl_file="script.tcl")

            # Verify the subprocess call
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert args[0][0] == "/opt/Xilinx/Vivado/2023.1/bin/vivado"
            assert args[0][1] == "-mode"
            assert args[0][2] == "batch"
            assert args[0][3] == "-source"
            assert args[0][4] == "script.tcl"

    @patch("src.vivado_handling.vivado_utils.find_vivado_installation")
    def test_run_vivado_command_vivado_not_found(self, mock_find_vivado):
        """Test running Vivado commands when Vivado is not found."""
        # Mock Vivado not found
        mock_find_vivado.return_value = None

        # Test running a command
        with pytest.raises(FileNotFoundError):
            run_vivado_command("-mode batch")

    @patch("shutil.which")
    @patch("os.path.exists")
    @patch("os.path.isdir")
    @patch("os.listdir")
    def test_find_vivado_in_tools_xilinx_version_pattern(
        self, mock_listdir, mock_isdir, mock_exists, mock_which
    ):
        """Test finding Vivado in /tools/Xilinx/[version]/Vivado pattern."""
        # Mock Vivado not in PATH
        mock_which.return_value = None

        def mock_exists_side_effect(path):
            return (
                path == "/tools/Xilinx"
                or "/tools/Xilinx/2023.1" in path
                or "/tools/Xilinx/2023.1/Vivado" in path
            )

        def mock_isdir_side_effect(path):
            return (
                path == "/tools/Xilinx"
                or path == "/tools/Xilinx/2023.1"
                or "/tools/Xilinx/2023.1/Vivado" in path
            )

        def mock_listdir_side_effect(path):
            if path == "/tools/Xilinx":
                return ["2021.2", "2022.1", "2023.1", "some_other_dir"]
            elif "/tools/Xilinx/2023.1/Vivado" in path:
                return ["2023.1"]  # Version subdirectory in Vivado folder
            return []

        mock_exists.side_effect = mock_exists_side_effect
        mock_isdir.side_effect = mock_isdir_side_effect
        mock_listdir.side_effect = mock_listdir_side_effect

        # Call the function
        with patch("os.path.isfile", return_value=True):
            with patch("subprocess.run") as mock_run:
                # Mock version command output
                mock_process = Mock()
                mock_process.returncode = 0
                mock_process.stdout = ""
                mock_run.return_value = mock_process

                result = find_vivado_installation()

                # Verify results - should find the version pattern installation
                assert result is not None
                assert "/tools/Xilinx/2023.1/Vivado" in result["path"]
                assert result["version"] == "2023.1"

    # Windows test removed as Windows support is not required

    @patch("shutil.which")
    @patch("os.path.exists")
    @patch("os.path.isdir")
    @patch("os.listdir")
    def test_find_vivado_tools_pattern_permission_error(
        self, mock_listdir, mock_isdir, mock_exists, mock_which
    ):
        """Test handling permission errors when scanning /tools/Xilinx/."""
        # Mock Vivado not in PATH
        mock_which.return_value = None

        # Mock /tools/Xilinx exists but causes permission error
        mock_exists.side_effect = lambda path: path == "/tools/Xilinx"
        mock_listdir.side_effect = PermissionError("Access denied")

        # Should not crash and continue with other search paths
        result = find_vivado_installation()

        # Should return None since no other paths are mocked to exist
        assert result is None

    @patch("shutil.which")
    @patch("os.path.exists")
    @patch("os.path.isdir")
    @patch("os.listdir")
    def test_find_vivado_tools_pattern_multiple_versions(
        self, mock_listdir, mock_isdir, mock_exists, mock_which
    ):
        """Test finding latest version when multiple versions exist in /tools/Xilinx/."""
        # Mock Vivado not in PATH
        mock_which.return_value = None

        def mock_exists_side_effect(path):
            return (
                path == "/tools/Xilinx"
                or "/tools/Xilinx/2023.2" in path
                or "/tools/Xilinx/2023.2/Vivado" in path
            )

        def mock_isdir_side_effect(path):
            return (
                path == "/tools/Xilinx"
                or path == "/tools/Xilinx/2023.2"
                or "/tools/Xilinx/2023.2/Vivado" in path
            )

        def mock_listdir_side_effect(path):
            if path == "/tools/Xilinx":
                # Multiple versions, should pick the latest (2023.2)
                return ["2021.2", "2022.1", "2023.1", "2023.2", "non_version_dir"]
            elif "/tools/Xilinx/2023.2/Vivado" in path:
                return ["2023.2"]
            return []

        mock_exists.side_effect = mock_exists_side_effect
        mock_isdir.side_effect = mock_isdir_side_effect
        mock_listdir.side_effect = mock_listdir_side_effect

        # Call the function
        with patch("os.path.isfile", return_value=True):
            with patch("subprocess.run") as mock_run:
                # Mock version command output
                mock_process = Mock()
                mock_process.returncode = 0
                mock_process.stdout = ""
                mock_run.return_value = mock_process

                result = find_vivado_installation()

                # Verify results - should find the latest version
                assert result is not None
                assert "/tools/Xilinx/2023.2/Vivado" in result["path"]
                assert result["version"] == "2023.2"

    def test_get_vivado_executable(self):
        """Test getting Vivado executable path."""
        with patch(
            "src.vivado_handling.vivado_utils.find_vivado_installation"
        ) as mock_find:
            # Test when Vivado is found
            mock_find.return_value = {
                "executable": "/opt/Xilinx/Vivado/2023.1/bin/vivado",
                "version": "2023.1",
                "path": "/opt/Xilinx/Vivado/2023.1",
                "bin_path": "/opt/Xilinx/Vivado/2023.1/bin",
            }

            result = get_vivado_executable()
            assert result == "/opt/Xilinx/Vivado/2023.1/bin/vivado"

            # Test when Vivado is not found
            mock_find.return_value = None
            result = get_vivado_executable()
            assert result is None

    @patch("src.vivado_handling.vivado_utils.find_vivado_installation")
    @patch("shutil.which")
    def test_run_vivado_command_fallback_to_path(self, mock_which, mock_find_vivado):
        """Test running Vivado commands with fallback to PATH."""
        # Mock discovery failure but PATH success
        mock_find_vivado.return_value = None
        mock_which.return_value = "/usr/bin/vivado"

        with patch("subprocess.run") as mock_run:
            mock_process = Mock()
            mock_process.returncode = 0
            mock_run.return_value = mock_process

            run_vivado_command("-mode batch")

            # Verify the subprocess call used PATH vivado
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert args[0][0] == "/usr/bin/vivado"

    @patch("src.vivado_handling.vivado_utils.find_vivado_installation")
    @patch("shutil.which")
    def test_run_vivado_command_use_discovered_path_false(
        self, mock_which, mock_find_vivado
    ):
        """Test running Vivado commands with use_discovered_path=False."""
        # Mock both discovery and PATH success
        mock_find_vivado.return_value = {
            "executable": "/opt/Xilinx/Vivado/2023.1/bin/vivado",
            "version": "2023.1",
        }
        mock_which.return_value = "/usr/bin/vivado"

        with patch("subprocess.run") as mock_run:
            mock_process = Mock()
            mock_process.returncode = 0
            mock_run.return_value = mock_process

            run_vivado_command("-mode batch", use_discovered_path=False)

            # Verify the subprocess call used PATH vivado, not discovered
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            assert args[0][0] == "/usr/bin/vivado"

    @patch("src.vivado_handling.vivado_utils.find_vivado_installation")
    @patch("shutil.which")
    def test_run_vivado_command_both_methods_fail(self, mock_which, mock_find_vivado):
        """Test running Vivado commands when both discovery and PATH fail."""
        # Mock both discovery and PATH failure
        mock_find_vivado.return_value = None
        mock_which.return_value = None

        with pytest.raises(FileNotFoundError) as exc_info:
            run_vivado_command("-mode batch")

        # Verify the error message includes helpful information
        error_msg = str(exc_info.value)
        assert "Vivado not found" in error_msg
        assert "PATH" in error_msg
        assert "XILINX_VIVADO" in error_msg


if __name__ == "__main__":
    pytest.main(["-v", __file__])
