#version 330

uniform float alpha;

in vec3 fragColor;
out vec4 finalColor;

void main() {
    finalColor = vec4(fragColor, alpha);
}
