resource "aws_ecr_repository" "annotation-backend" {
    name = "staff/annotation-backend"
}
resource "aws_ecr_repository" "annotation-frontend" {
    name = "staff/annotation-frontend"
}

