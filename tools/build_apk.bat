@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
rem 打包安卓 APK：前端构建 -> cap sync -> gradle assembleDebug -> 复制到项目根目录
set ROOT=%~dp0..
set "JDK_DEFAULT=%TEMP%\android-build\jdk\jdk-17.0.20.1+1"
set "SDK_DEFAULT=%TEMP%\android-sdk"

if "%JAVA_HOME%"=="" if exist "%JDK_DEFAULT%" set JAVA_HOME=%JDK_DEFAULT%
if "%ANDROID_HOME%"=="" if exist "%SDK_DEFAULT%" set ANDROID_HOME=%SDK_DEFAULT%
if "%ANDROID_HOME%"=="" if exist "%SDK_DEFAULT%" set ANDROID_SDK_ROOT=%SDK_DEFAULT%

if "%JAVA_HOME%"=="" (
  echo [错误] 找不到 JDK 17，请先安装并设置 JAVA_HOME
  exit /b 1
)
if "%ANDROID_HOME%"=="" (
  echo [错误] 找不到 Android SDK，请先安装并设置 ANDROID_HOME ^(需要 platforms;android-34 与 build-tools;34.0.0^)
  exit /b 1
)

echo == 1/4 构建前端 ==
pushd "%ROOT%\frontend"
call pnpm build || (popd & exit /b 1)

echo == 2/4 同步到安卓工程 ==
call npx cap sync android || (popd & exit /b 1)

echo == 3/4 Gradle 打包 ==
cd android
if not exist "local.properties" (
  echo sdk.dir=%ANDROID_HOME:\=\\%> local.properties
)
call gradlew.bat assembleDebug --no-daemon || (popd & exit /b 1)

echo == 4/4 复制 APK ==
set APK=%ROOT%\frontend\android\app\build\outputs\apk\debug\app-debug.apk
if not exist "%APK%" (
  echo [错误] 没有找到构建产物：%APK%
  popd & exit /b 1
)
copy /y "%APK%" "%ROOT%\日程规划-Android.apk" >nul
popd
echo.
echo 完成：%ROOT%\日程规划-Android.apk
echo 安装到手机：把 APK 传到手机（微信/QQ 传文件或用数据线），点开安装。
echo 手机和电脑要连同一个 WiFi。App 首次打开需填写电脑地址和电脑设置中显示的配对密钥。
endlocal
