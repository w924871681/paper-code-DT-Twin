$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    foreach ($document in @('main.tex', 'supplementary.tex')) {
        foreach ($pass in 1..2) {
            & pdflatex -interaction=nonstopmode -halt-on-error -file-line-error $document
            if ($LASTEXITCODE -ne 0) {
                throw "Compilation failed: $document, pass $pass"
            }
        }
    }
} finally {
    Pop-Location
}
