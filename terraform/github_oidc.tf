# Permite que los workflows de GitHub Actions de este repo concreto
# asuman un rol IAM mediante OIDC, sin credenciales estáticas
# guardadas como secret. AWS ya no valida el thumbprint del proveedor
# de GitHub contra la lista declarada (verifica la cadena TLS
# directamente desde julio de 2023); el valor de abajo se mantiene
# solo porque el recurso lo exige sintácticamente, no tiene efecto
# real.

resource "aws_iam_openid_connect_provider" "github_actions" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

data "aws_iam_policy_document" "github_actions_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github_actions.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Solo workflows que corren en este repo (cualquier rama/PR/
    # workflow_dispatch dentro de él) pueden asumir el rol. Un PR
    # desde un fork no cuenta: GitHub no concede id-token/secrets a
    # "pull_request" de forks por defecto, así que no hace falta
    # restringir más para un repo de un solo mantenedor.
    #
    # Usa el formato de claim "sub" inmutable (con @<owner_id> y
    # @<repo_id>), no el basado solo en nombre: los repos creados a
    # partir del 15/07/2026 lo emiten así por defecto, para que un
    # cambio de nombre de usuario/repo no reasigne esta confianza a
    # otra cuenta. El formato antiguo (repo:usuario/repo:*) da
    # "Not authorized to perform sts:AssumeRoleWithWebIdentity" contra
    # este tipo de repo, aunque el resto de la política sea correcto
    # — verificado con un token real, no es una suposición.
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${local.github_owner_name}@${var.github_owner_id}/${local.github_repo_name}@${var.github_repository_id}:*"]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  name               = "${var.project}-${var.environment}-github-actions"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume.json
}

# Mismo compromiso que terraform-deploy (ver README, "Decisiones y por
# qué"): least privilege exacto por recurso es fricción sin beneficio
# real de seguridad en una cuenta personal de un solo desarrollador.
# El límite de seguridad real aquí es el propio OIDC: nadie sin acceso
# de escritura a este repo puede asumir el rol.
resource "aws_iam_role_policy_attachment" "github_actions_power_user" {
  role       = aws_iam_role.github_actions.name
  policy_arn = "arn:aws:iam::aws:policy/PowerUserAccess"
}

resource "aws_iam_role_policy_attachment" "github_actions_iam" {
  role       = aws_iam_role.github_actions.name
  policy_arn = "arn:aws:iam::aws:policy/IAMFullAccess"
}
