#version 330

uniform mat4 projectionMatrix;
uniform mat4 modelViewMatrix;
uniform vec3 cameraPosition;

uniform float heightFactor;

layout(location = 0) in vec3 position;
layout(location = 1) in vec3 normal;

out vec3 fragPosition;
out vec3 fragNormal;

void main() {
    vec4 eyePosition = modelViewMatrix * vec4(position * vec3(1.0, 1.0, heightFactor), 1.0);
    gl_Position = projectionMatrix * eyePosition;
    
    fragPosition = eyePosition.xyz;
    fragNormal = normal;
}
