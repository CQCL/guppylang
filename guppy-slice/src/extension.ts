import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { workspace, window, commands, languages, ExtensionContext, TextDocument } from 'vscode';

import {
	LanguageClient,
	LanguageClientOptions,
	ServerOptions,
	TransportKind
} from 'vscode-languageclient/node';

let client: LanguageClient;

export function activate(context: vscode.ExtensionContext) {
	console.log('Extension "guppy-slice" is now active!');

	let toggleCommand = vscode.commands.registerCommand('guppy-slice.toggleFocusMode', () => {
        client.sendRequest('workspace/executeCommand', { command: 'toggleFocusMode' });
    });

    context.subscriptions.push(toggleCommand);

    const serverModule = context.asAbsolutePath('server/server.py');
	console.log(`Starting server at: ${serverModule}`);
    const serverOptions: ServerOptions = {
		// TODO: Need better way of getting correct Python executable.
        // command: 'import os; os.environ[\'_\']',
		command: '/Users/tatiana.sedelnikov/Documents/Code/guppylang/.devenv/state/venv/bin/python',
        args: [serverModule],
        transport: TransportKind.stdio,
    };
	

    const clientOptions: LanguageClientOptions = {
        documentSelector: [{ scheme: 'file', language: 'python' }],
		synchronize: {
            fileEvents: workspace.createFileSystemWatcher('**/*.py'),
        },
    };

    client = new LanguageClient('guppySliceServer', 'Guppy Slice Extension', serverOptions, clientOptions);
    client.start();
}

// This method is called when your extension is deactivated
export function deactivate() {}
