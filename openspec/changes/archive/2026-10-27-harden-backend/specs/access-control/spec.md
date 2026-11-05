# Spec Delta

## MODIFIED Requirements

### Requirement: Проверка Origin на мутациях

Система SHALL отклонять мутирующие запросы, у которых заголовок Origin не
совпадает с адресом приложения, и MUST отклонять мутации без Origin в
production. В dev и test запросы без Origin SHALL пропускаться.

#### Scenario: Запрос с чужим Origin
- **WHEN** POST-запрос приходит с Origin другого сайта
- **THEN** система отвечает 403 и не выполняет изменение

#### Scenario: Мутация без Origin в production
- **WHEN** POST-запрос приходит без Origin, а приложение работает в production
- **THEN** система отвечает 403 и не выполняет изменение

#### Scenario: Мутация без Origin в dev
- **WHEN** POST-запрос приходит без Origin в dev или test
- **THEN** система выполняет изменение
