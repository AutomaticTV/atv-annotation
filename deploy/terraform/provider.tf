provider "aws" {
  region = "eu-west-1"
}


terraform {
  backend "s3" {
    bucket = "atv-terraform-backend"
    key    = "atv-annotation"
    region = "eu-west-1"
  }
}

