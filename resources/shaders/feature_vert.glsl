#version 330

uniform mat4 projectionMatrix;
uniform mat4 modelViewMatrix;
uniform vec3 cameraPosition;

layout(location = 0) in vec3 position;

void main() {
    vec4 eyePosition = modelViewMatrix * vec4(position  + vec3(0., 50, 0.), 1.0);
    gl_Position = projectionMatrix * eyePosition;
}
