#version 330

uniform mat4 projectionMatrix;
uniform mat4 modelViewMatrix;
uniform vec3 cameraPosition;

layout(location = 0) in vec3 position;

const vec4 scale = vec4(10.);

void main() {
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0) * scale;
}
