import os

from click.testing import CliRunner

from mcp_jenkins import main

JENKINS_ENV_VARS = (
    'jenkins_url',
    'jenkins_username',
    'jenkins_password',
    'jenkins_timeout',
    'jenkins_verify_ssl',
    'jenkins_session_singleton',
)


def test_main_stdio(mocker):
    mocker.patch('mcp_jenkins.asyncio')
    mock_mcp = mocker.patch('mcp_jenkins.server.mcp')

    CliRunner().invoke(main, ['--transport', 'stdio'])

    mock_mcp.run_async.assert_called_once_with(transport='stdio')


def test_main_sse(mocker):
    mocker.patch('mcp_jenkins.asyncio')
    mock_mcp = mocker.patch('mcp_jenkins.server.mcp')

    CliRunner().invoke(main, ['--transport', 'sse', '--host', '127.0.0.1', '--port', '9887'])
    mock_mcp.run_async.assert_called_once_with(transport='sse', host='127.0.0.1', port=9887)


def test_main_streamable_http(mocker):
    mocker.patch('mcp_jenkins.asyncio')
    mock_mcp = mocker.patch('mcp_jenkins.server.mcp')

    CliRunner().invoke(
        main,
        ['--transport', 'streamable-http', '--host', '127.0.0.1', '--port', '9887'],
    )
    mock_mcp.run_async.assert_called_once_with(transport='streamable-http', host='127.0.0.1', port=9887)


def test_main(mocker):
    mocker.patch('mcp_jenkins.asyncio')
    mock_mcp = mocker.patch('mcp_jenkins.server.mcp')

    CliRunner().invoke(
        main,
        [
            '--transport',
            'stdio',
            '--jenkins-url',
            'https://example.com',
            '--jenkins-username',
            'username',
            '--jenkins-password',
            'password',
            '--jenkins-timeout',
            '30',
        ],
    )

    mock_mcp.run_async.assert_called_once_with(transport='stdio')


def test_main_env_vars(mocker, monkeypatch):
    mocker.patch('mcp_jenkins.asyncio')
    mocker.patch('mcp_jenkins.server.mcp')

    for key in JENKINS_ENV_VARS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('JENKINS_URL', 'https://env.example.com')
    monkeypatch.setenv('JENKINS_USERNAME', 'env-username')
    monkeypatch.setenv('JENKINS_PASSWORD', 'env-password')
    monkeypatch.setenv('JENKINS_TIMEOUT', '42')
    monkeypatch.setenv('JENKINS_VERIFY_SSL', 'false')

    result = CliRunner().invoke(main, ['--transport', 'stdio'])

    assert result.exit_code == 0
    assert os.environ['jenkins_url'] == 'https://env.example.com'
    assert os.environ['jenkins_username'] == 'env-username'
    assert os.environ['jenkins_password'] == 'env-password'
    assert os.environ['jenkins_timeout'] == '42'
    assert os.environ['jenkins_verify_ssl'] == 'false'


def test_main_cli_arg_overrides_env_var(mocker, monkeypatch):
    mocker.patch('mcp_jenkins.asyncio')
    mocker.patch('mcp_jenkins.server.mcp')

    for key in JENKINS_ENV_VARS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('JENKINS_URL', 'https://env.example.com')

    result = CliRunner().invoke(main, ['--transport', 'stdio', '--jenkins-url', 'https://cli.example.com'])

    assert result.exit_code == 0
    assert os.environ['jenkins_url'] == 'https://cli.example.com'


def test_main_env_file_explicit(mocker, monkeypatch, tmp_path):
    mocker.patch('mcp_jenkins.asyncio')
    mocker.patch('mcp_jenkins.server.mcp')

    for key in JENKINS_ENV_VARS:
        monkeypatch.delenv(key, raising=False)
    for key in ('JENKINS_URL', 'JENKINS_USERNAME', 'JENKINS_PASSWORD'):
        monkeypatch.delenv(key, raising=False)

    env_file = tmp_path / 'custom.env'
    env_file.write_text(
        'JENKINS_URL=https://file.example.com\nJENKINS_USERNAME=file-username\nJENKINS_PASSWORD=file-password\n'
    )

    result = CliRunner().invoke(main, ['--env-file', str(env_file), '--transport', 'stdio'])

    assert result.exit_code == 0
    assert os.environ['jenkins_url'] == 'https://file.example.com'
    assert os.environ['jenkins_username'] == 'file-username'
    assert os.environ['jenkins_password'] == 'file-password'


def test_main_env_file_missing_path(mocker):
    mocker.patch('mcp_jenkins.asyncio')
    mocker.patch('mcp_jenkins.server.mcp')

    result = CliRunner().invoke(main, ['--env-file', 'does-not-exist.env', '--transport', 'stdio'])

    assert result.exit_code != 0


def test_main_env_file_autodiscovery(mocker, monkeypatch, tmp_path):
    mocker.patch('mcp_jenkins.asyncio')
    mocker.patch('mcp_jenkins.server.mcp')

    for key in JENKINS_ENV_VARS:
        monkeypatch.delenv(key, raising=False)
    for key in ('JENKINS_URL', 'JENKINS_USERNAME', 'JENKINS_PASSWORD'):
        monkeypatch.delenv(key, raising=False)

    (tmp_path / '.env').write_text(
        'JENKINS_URL=https://auto.example.com\nJENKINS_USERNAME=auto-username\nJENKINS_PASSWORD=auto-password\n'
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ['--transport', 'stdio'])

    assert result.exit_code == 0
    assert os.environ['jenkins_url'] == 'https://auto.example.com'
    assert os.environ['jenkins_username'] == 'auto-username'
    assert os.environ['jenkins_password'] == 'auto-password'
