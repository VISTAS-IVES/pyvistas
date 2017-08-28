#version 330 core

uniform vec3 color;
uniform bool hideNoData;
uniform float noDataValue;

out vec4 finalColor;

// Filter on magnitude
uniform bool filterMag;
uniform float magMin;
uniform float magMax;
//in float fMag;

// Filter on attribute value
//in float fValue;

void main()
{
    //if (filterMag && (fMag > magMax || fMag < magMin)) discard;
    //if (hideNoData && (round(fValue) == round(noDataValue))) discard;
    finalColor = vec4(color, 1.0f);
}