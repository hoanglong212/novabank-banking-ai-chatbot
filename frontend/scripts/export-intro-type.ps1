# Outline local system typography once; the browser needs no fonts or raster text.
Add-Type -AssemblyName System.Drawing
$definitions = @(
  @('core', 'N', 42, 'Arial', 1),
  @('nova', 'nova', 52, 'Arial', 1),
  @('bank', 'bank', 52, 'Arial', 1),
  @('question', '?', 28, 'Arial', 1),
  @('payment', '$', 25, 'Arial', 1),
  @('loading', 'LOADING QR PAYMENTS...', 10, 'Consolas', 0),
  @('sorting', 'SORTING THE DETAILS...', 10, 'Consolas', 0),
  @('almost', 'ALMOST THERE...', 10, 'Consolas', 0),
  @('ready', 'READY', 10, 'Consolas', 0),
  @('securing', 'SECURING CONNECTION...', 10, 'Consolas', 0),
  @('syncing', 'SYNCING FAQ ANSWERS...', 10, 'Consolas', 0),
  @('indexing', 'INDEXING TRANSACTIONS...', 10, 'Consolas', 0),
  @('balances', 'FETCHING BALANCES...', 10, 'Consolas', 0),
  @('reminders', 'SCHEDULING REMINDERS...', 10, 'Consolas', 0),
  @('p0', '0%', 10, 'Arial', 1),
  @('p24', '24%', 10, 'Arial', 1),
  @('p52', '52%', 10, 'Arial', 1),
  @('p78', '78%', 10, 'Arial', 1),
  @('p100', '100%', 10, 'Arial', 1)
)
$definitions += @(0..100 | ForEach-Object { ,@("p$_", "$_%", 10, 'Arial', 1) })
$result = @{}
foreach ($definition in $definitions) {
  $path = New-Object System.Drawing.Drawing2D.GraphicsPath
  $family = New-Object System.Drawing.FontFamily($definition[3])
  $path.AddString($definition[1], $family, [int]$definition[4], [single]$definition[2], [System.Drawing.PointF]::new(0,0), [System.Drawing.StringFormat]::GenericTypographic)
  $bounds = $path.GetBounds()
  $points = $path.PathPoints
  $types = $path.PathTypes
  $data = for ($i=0; $i -lt $points.Length; $i++) { ,@([math]::Round($points[$i].X-$bounds.X,3), [math]::Round($points[$i].Y-$bounds.Y,3), [int]$types[$i]) }
  $result[$definition[0]] = @{ width=$bounds.Width; height=$bounds.Height; points=@($data) }
  $path.Dispose()
  $family.Dispose()
}
$destination = Join-Path $PSScriptRoot 'nova-intro-outlines.json'
[IO.File]::WriteAllText($destination, ($result | ConvertTo-Json -Depth 8 -Compress), [Text.UTF8Encoding]::new($false))
Write-Output $destination

