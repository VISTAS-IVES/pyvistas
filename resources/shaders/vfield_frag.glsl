#version 330 core

in vec3 fColor;
out vec4 color;

// Filter on magnitude
uniform bool filterMag;
uniform float magMin;
uniform float magMax;
in float fMag;

void main()
{
    if (filterMag && (fMag > magMax || fMag < magMin)) discard;
    color = vec4(fColor, 1.0f);
}