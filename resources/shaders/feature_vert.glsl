#version 330

uniform mat4 projectionMatrix;
uniform mat4 modelViewMatrix;
uniform vec3 cameraPosition;

uniform float heightMultiplier;
uniform float heightOffset;

layout(location = 0) in vec3 position;
layout(location = 3) in vec3 color;

out vec3 fragColor;

void main() {
    vec4 eyePosition = modelViewMatrix * vec4(position * vec3(1.0, heightMultiplier, 1.0) + vec3(0, heightOffset, 0), 1.0);
    gl_Position = projectionMatrix * eyePosition;
    fragColor = color;
}