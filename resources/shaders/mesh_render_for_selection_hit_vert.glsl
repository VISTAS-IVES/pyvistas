#version 330

uniform mat4 projectionMatrix;
uniform mat4 modelViewMatrix;
uniform vec4 color;

in vec3 position;

out vec4 finalColor;

void main() {
	vec4 eyePosition = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * eyePosition;
    finalColor = color;
}