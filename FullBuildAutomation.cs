using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.Networking;  // For UnityWebRequest if needed
using Debug = UnityEngine.Debug;
public class FullBuildAutomation
{
    private static string buildRoot = "Builds";
    

    private static string[] GetEnabledScenes()
    {
        return EditorBuildSettings.scenes
            .Where(s => s.enabled)
            .Select(s => s.path)
            .ToArray();
    }

    [MenuItem("Build/Run Full Automation")]
    public static void RunFullBuildAutomation()
    {
        try
        {
            // 1. Create directories
            Directory.CreateDirectory(buildRoot);
            string webglPath = Path.Combine(buildRoot, "WebGL");
            string linuxFolder = Path.Combine(buildRoot, "Linux");
            string windowsFolder = Path.Combine(buildRoot, "Windows");

            Directory.CreateDirectory(webglPath);
            Directory.CreateDirectory(linuxFolder);
            Directory.CreateDirectory(windowsFolder);

            string[] scenes = GetEnabledScenes();

            // 2. WebGL build with no compression
            PlayerSettings.WebGL.compressionFormat = WebGLCompressionFormat.Disabled;
            Debug.Log("Starting WebGL build...");
            var webglReport = BuildPipeline.BuildPlayer(scenes, webglPath, BuildTarget.WebGL, BuildOptions.None);
            if (webglReport.summary.result != BuildResult.Succeeded)
            {
                Debug.LogError("WebGL build failed!");
                SendDiscordMessage(" WebGL build failed!");
                return;
            }
            Debug.Log("WebGL build succeeded.");
            SendDiscordMessage(" WebGL build succeeded.");

            // 3. Linux build
            Debug.Log("Starting Linux build...");
            var linuxReport = BuildPipeline.BuildPlayer(scenes, linuxFolder, BuildTarget.StandaloneLinux64, BuildOptions.None);
            if (linuxReport.summary.result != BuildResult.Succeeded)
            {
                Debug.LogError("Linux build failed!");
                SendDiscordMessage("Linux build failed!");
                return;
            }
            Debug.Log("Linux build succeeded.");
            SendDiscordMessage(" Linux build succeeded.");

            // 4. Windows build
            Debug.Log("Starting Windows build...");
            var windowsReport = BuildPipeline.BuildPlayer(scenes, windowsFolder, BuildTarget.StandaloneWindows64, BuildOptions.None);
            if (windowsReport.summary.result != BuildResult.Succeeded)
            {
                Debug.LogError("Windows build failed!");
                SendDiscordMessage(" Windows build failed!");
                return;
            }
            Debug.Log("Windows build succeeded.");
            SendDiscordMessage(" Windows build succeeded.");

            // 5. Run generate.py in buildRoot folder
            RunPythonScript("generate.py", buildRoot);
            Debug.Log("generate.py script executed.");
            SendDiscordMessage(" Python generate.py script executed.");

        }
        catch (Exception ex)
        {
            Debug.LogError($"Build automation failed: {ex.Message}");
            SendDiscordMessage($"❌ Build automation error: {ex.Message}");
        }
    }

   

    private static void RunPythonScript(string scriptName, string workingDirectory)
    {
        try
        {
            var processInfo = new ProcessStartInfo
            {
                FileName = "python3", // assuming python3 is in PATH on Linux
                Arguments = scriptName,
                WorkingDirectory = Path.GetFullPath(workingDirectory),
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
            };

            using (var process = Process.Start(processInfo))
            {
                process.WaitForExit();

                string output = process.StandardOutput.ReadToEnd();
                string error = process.StandardError.ReadToEnd();

                if (!string.IsNullOrEmpty(output))
                    Debug.Log($"Python output: {output}");
                if (!string.IsNullOrEmpty(error))
                    Debug.LogError($"Python error: {error}");

                if (process.ExitCode != 0)
                {
                    Debug.LogError($"Python script exited with code {process.ExitCode}");
                }
            }
        }
        catch (Exception ex)
        {
            Debug.LogError("Failed to run python script: " + ex.Message);
        }
    }
}

