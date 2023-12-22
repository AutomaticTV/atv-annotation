locals {
  public_elb = [""]
}

data "aws_route53_zone" "" {
  name = ""
}


resource "aws_route53_record" "annotation-frontend" {
  zone_id = data.aws_route53_zone..zone_id
  name    = ""
  type    = "A"
  ttl     = "300"
  records = [""] 
}

resource "aws_route53_record" "annotation-backend" {
  zone_id = data.aws_route53_zone..zone_id
  name    = ""
  type    = "A"
  ttl     = "300"
  records = [""] 
}


resource "aws_route53_record" "annotation-api-proxy" {
  zone_id = data.aws_route53_zone..zone_id
  name    = ""
  type    = "CNAME"
  ttl     = "300"
  records = local.public_elb
}
