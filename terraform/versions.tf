terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # El backend remoto (S3 + DynamoDB para locking) se configura una vez
  # exista el bucket de estado. Hasta entonces el estado es local y no
  # se versiona (ver .gitignore).
}
