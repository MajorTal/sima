# The SecureString parameters are created outside Terraform first (copied
# from the running stack's values); these blocks adopt them into state.
# Parameter names follow modules/secrets: /secrets/sima/<environment>/<name>.

import {
  to = module.secrets.aws_ssm_parameter.database_url
  id = "/secrets/sima/sima/database-url"
}

import {
  to = module.secrets.aws_ssm_parameter.telegram_bot_token
  id = "/secrets/sima/sima/telegram-bot-token"
}

import {
  to = module.secrets.aws_ssm_parameter.telegram_chat_id
  id = "/secrets/sima/sima/telegram-chat-id"
}

import {
  to = module.secrets.aws_ssm_parameter.openai_api_key
  id = "/secrets/sima/sima/openai-api-key"
}

import {
  to = module.secrets.aws_ssm_parameter.jwt_secret
  id = "/secrets/sima/sima/jwt-secret"
}

import {
  to = module.secrets.aws_ssm_parameter.lab_password
  id = "/secrets/sima/sima/lab-password"
}

import {
  to = module.secrets.aws_ssm_parameter.admin_username
  id = "/secrets/sima/sima/admin-username"
}

import {
  to = module.secrets.aws_ssm_parameter.admin_password
  id = "/secrets/sima/sima/admin-password"
}
