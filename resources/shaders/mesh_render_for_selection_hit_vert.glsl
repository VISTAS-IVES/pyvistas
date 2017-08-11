#version 330

uniform mat4 projectionMatrix;
uniform mat4 modelViewMatrix;

in vec3 position;

void main() {
	vec4 eyePosition = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * eyePosition;
}
