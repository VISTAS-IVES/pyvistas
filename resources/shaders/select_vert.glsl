#version 330

uniform float width;
uniform float height;

layout(location = 0) in vec3 position;

void main() {
    gl_Position = vec4(position.x / width * 2 - 1., 1. - position.y / height * 2, 0, 1);
}
