terraform {
  required_version = ">= 1.7.0, < 2.0.0"
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
provider "aws" { region = var.region }
variable "region" {
  type = string
  default = "ap-southeast-1"
}
variable "vpc_id" { type = string }
variable "private_subnet_id" { type = string }
variable "ami_id" {
  type = string
  description = "Approved AL2023 AMI with SSM agent. Operator selects current image."
}
variable "image" {
  type = string
  description = "Reviewed SunSOC image URI pinned by digest, accessible from the private subnet."
  validation {
    condition = can(regex("^[A-Za-z0-9._:/-]+@sha256:[a-f0-9]{64}$", var.image))
    error_message = "Supply an immutable container image URI ending in @sha256:<64 lowercase hex characters>."
  }
}
variable "teams" {
  type = set(string)
  default = ["team-a", "team-b"]
  validation {
    condition = alltrue([for team in var.teams : can(regex("^[a-z][a-z0-9-]{1,24}$", team))])
    error_message = "Team IDs must be short lowercase names."
  }
}
resource "aws_security_group" "range" {
  name_prefix = "sunsoc-private-"
  description = "No inbound access; SSM port forwarding only"
  vpc_id = var.vpc_id
  egress {
    from_port = 443
    to_port = 443
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Project = "SunSOC", Purpose = "Training" }
}
resource "aws_iam_role" "range" {
  name_prefix = "sunsoc-ssm-"
  assume_role_policy = jsonencode({Version="2012-10-17",Statement=[{Effect="Allow",Principal={Service="ec2.amazonaws.com"},Action="sts:AssumeRole"}]})
}
resource "aws_iam_role_policy_attachment" "ssm" {
  role = aws_iam_role.range.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
resource "aws_iam_instance_profile" "range" {
  name_prefix = "sunsoc-"
  role = aws_iam_role.range.name
}
resource "aws_instance" "team" {
  for_each = var.teams
  ami = var.ami_id
  instance_type = "t3.small"
  subnet_id = var.private_subnet_id
  associate_public_ip_address = false
  vpc_security_group_ids = [aws_security_group.range.id]
  iam_instance_profile = aws_iam_instance_profile.range.name
  metadata_options { http_tokens = "required" }
  root_block_device {
    encrypted = true
    volume_size = 16
    volume_type = "gp3"
  }
  user_data = templatefile("${path.module}/bootstrap.sh.tftpl", { image = var.image })
  user_data_replace_on_change = true
  tags = { Name="sunsoc-${each.key}",Project="SunSOC",Team=each.key }
}
output "team_instances" { value = { for key, instance in aws_instance.team : key => instance.id } }
