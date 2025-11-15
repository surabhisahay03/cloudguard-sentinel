{{/*
Return the short chart/app name (can be overridden by .Values.nameOverride).
*/}}
{{- define "cloudguard.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Return a fully qualified name for resources: <release>-<name>
Respects .Values.fullnameOverride if set.
*/}}
{{- define "cloudguard.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := include "cloudguard.name" . -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Common labels applied to every resource.
*/}}
{{- define "cloudguard.labels" -}}
app.kubernetes.io/name: {{ include "cloudguard.name" . }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels for matching pods/services.
*/}}
{{- define "cloudguard.selectorLabels" -}}
app.kubernetes.io/name: {{ include "cloudguard.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
