import os
import requests
import html

USERNAME = "iitking"

# GitHub contribution calendar
url = f"https://github.com/users/{USERNAME}/contributions"

response = requests.get(url, timeout=20)
response.raise_for_status()

text = response.text

# Extract contribution SVG
start = text.find("<svg")
end = text.find("</svg>")

if start == -1 or end == -1:
    raise RuntimeError("GitHub contribution graph could not be found")

svg = text[start:end + 6]

# Basic SVG dimensions
width = 950
height = 180

# Create animated custom SVG
output = f'''<svg xmlns="http://www.w3.org/2000/svg"
     width="{width}"
     height="{height}"
     viewBox="0 0 {width} {height}">

  <style>
    .snake {{
      fill: none;
      stroke: #2da44e;
      stroke-width: 7;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}

    .head {{
      fill: #2da44e;
    }}

    .block {{
      fill: #216e39;
    }}

    @keyframes grow {{
      0% {{
        stroke-dashoffset: 1000;
      }}
      100% {{
        stroke-dashoffset: 0;
      }}
    }}

    .body {{
      stroke-dasharray: 1000;
      stroke-dashoffset: 1000;
      animation: grow 12s linear infinite;
    }}
  </style>

  <rect width="100%" height="100%" fill="transparent"/>

  <!-- Contribution blocks -->
  <g opacity="0.9">
'''

# Add contribution-like grid
for y in range(7):
    for x in range(53):
        px = 20 + x * 17
        py = 20 + y * 17

        output += f'''
        <rect class="block"
              x="{px}"
              y="{py}"
              width="12"
              height="12"
              rx="2">
          <animate
            attributeName="opacity"
            values="1;1;0"
            begin="{(x + y * 53) * 0.025}s"
            dur="0.4s"
            repeatCount="indefinite"/>
        </rect>
'''

output += '''
  </g>

  <!-- Growing snake -->
  <path
    class="snake body"
    d="
      M20 140
      C80 140 80 30 140 30
      S200 140 260 140
      S320 30 380 30
      S440 140 500 140
      S560 30 620 30
      S680 140 740 140
      S800 30 860 30
      S900 100 930 100
    />

  <!-- Snake head -->
  <circle class="head" cx="930" cy="100" r="8"/>

</svg>
'''

os.makedirs("dist", exist_ok=True)

with open("dist/github-snake-growing.svg", "w", encoding="utf-8") as f:
    f.write(output)

print("Snake generated successfully!")
