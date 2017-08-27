#version 330

uniform sampler2D overlay;

in vec2 fragUv;

out vec4 finalColor;

void main() {
    finalColor = texture(overlay, fragUv);
}
