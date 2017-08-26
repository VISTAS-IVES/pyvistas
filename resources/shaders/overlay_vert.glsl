#version 330

uniform float width;
uniform float height;

layout(location = 0) in vec3 position;
layout(location = 2) in vec2 uv;

out vec2 fragUv;

void main() {
    gl_Position = vec4(position.x / width * 2 - 1., 1. - position.y / height * 2, 0, 1);
    fragUv = vec2(uv.x, 1. - uv.y);
}
