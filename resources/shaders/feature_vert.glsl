#version 330

uniform mat4 projectionMatrix;
uniform mat4 modelViewMatrix;
uniform vec3 cameraPosition;

uniform float heightFactor;
uniform float heightOffset;

layout(location = 0) in vec3 position;
layout(location = 1) in vec3 normal;
layout(location = 3) in vec3 color;

out vec3 fragColor;
out vec3 fragPosition;
out vec3 fragNormal;

void main() {
	vec3 scale = vec3(1.0, 1.0, heightFactor);
    vec4 eyePosition = modelViewMatrix * vec4(position * scale + vec3(0, 0, heightOffset), 1.0);
    gl_Position = projectionMatrix * eyePosition;
    fragPosition = eyePosition.xyz;
    fragColor = color;
    fragNormal = normal;
}
