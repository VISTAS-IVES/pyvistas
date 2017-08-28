#version 330 core

layout(location = 0) in vec3 position;
layout(location = 4) in vec3 offset;
//layout(location = 5) in float direction;
//layout(location = 6) in float tilt;
//layout(location = 7) in float magnitude;
//layout(location = 8) in float value;

uniform float scale;
uniform vec3 vertexScalars;
uniform float timer;
uniform bool scaleMag;
uniform float vectorSpeed;

uniform mat4 projectionMatrix;
uniform mat4 modelViewMatrix;

out float fMag;
out float fValue;

mat3  rotateXYZ(vec3 r) {
    float cx = cos(radians(r.x));
    float sx = sin(radians(r.x));
    float cy = cos(radians(r.y));
    float sy = sin(radians(r.y));
    float cz = cos(radians(r.z));
    float sz = sin(radians(r.z));
    return mat3(cy * cz, cx * sz + sx * sy * cz, sx * sz - cx * sy * cz,
                -cy * sz, cx * cz - sx * sy * sz, sx * cz + cx * sy * sz,
                sy, -sx * cy, cx * cy);
}

/*
float scaleMagnitude() {
    float mag = magnitude;
    if (scaleMag) {
        mag = log(log(mag));
    }
    else {
        mag = 1.0;
    }
    return mag;
}

vec3 animateInstance() {
    return position + vec3(0, 0, -timer * .5) * abs(log(log(magnitude + 1))) * vectorSpeed;
}
*/

vec3 rotateAndScaleInstance() {
    return position;
}

void main() {
    //gl_Position = projectionMatrix * modelViewMatrix * vec4(rotateAndScaleInstance() + offset * vertexScalars, 1.0);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position * scale + offset * vertexScalars, 1.0);
    //fMag = magnitude;
    //fValue = value;
}