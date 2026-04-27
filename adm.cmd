@echo off
setlocal
pushd "%~dp0"
python -m adm_pipeline.cli %*
set EXITCODE=%ERRORLEVEL%
popd
exit /b %EXITCODE%
