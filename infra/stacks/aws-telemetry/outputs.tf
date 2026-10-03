output "landing_bucket" {
  description = "Where telemetry lands. Destroyed with the window — do not reference it from anything."
  value       = aws_s3_bucket.landing.id
}

output "thing_name" {
  value = aws_iot_thing.conveyor.name
}

output "topic" {
  description = "The only topic this device may publish to. It may not subscribe at all (ADR-005)."
  value       = "limen/plant/${aws_iot_thing.conveyor.name}/+"
}

output "evidence_note" {
  description = "Copied into the evidence record so a reader is never misled about what is running."
  value       = "Applied and destroyed inside a single workflow run. Nothing in this output still exists."
}
