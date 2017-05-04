#version 330

uniform mat4 projectionMatrix;
uniform mat4 modelViewMatrix;
uniform vec3 cameraPosition;

in vec3 position;
in vec3 normal;

out vec3 fragPosition;
out vec3 fragNormal;

void main() {
    vec4 eyePosition = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * eyePosition;
    fragPosition = eyePosition.xyz;
    fragNormal = normal;
}
