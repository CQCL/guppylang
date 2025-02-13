import * as vscode from 'vscode';
import { workspace} from 'vscode';

import {
	LanguageClient,
	LanguageClientOptions,
	ServerOptions,
	TransportKind
} from 'vscode-languageclient/node';

let client: LanguageClient;

let focusMode = false;

export function activate(context: vscode.ExtensionContext) {
	console.log('Extension "guppy-slice" is now active!');

    function computeDependenciesRequest() {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage("No active file.");
            return;
        }

        const filePath = editor.document.uri.toString();
        const params = { uri: filePath };

        client.sendRequest("workspace/executeCommand", {
            command: "computeDependencies",
            arguments: [params]
        }).then((response) => {
                if (response) {
                    vscode.window.showInformationMessage(`Dependencies computed successfully.`);
                } else {
                    vscode.window.showWarningMessage(`Dependency computation failed.`);
                }
            });
    }

    // Command: (re-)compute dependencies when focus mode is enabled.
    let toggleCommand = vscode.commands.registerCommand('extension.toggleFocusMode', () => {
        focusMode = !focusMode;
        if (focusMode) {
            computeDependenciesRequest();
        } else {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showErrorMessage("No active file.");
                return;
            }
            const filePath = editor.document.uri.toString();
            client.sendRequest("workspace/executeCommand", {
                command: "clearDiagnostics",
                arguments: [{ uri: filePath }]
            });
        }
    });
    context.subscriptions.push(toggleCommand);

    // On save: (re-)compute dependencies if focus mode is enabled (could do on change but performance considerations).
    // TODO: Use document argument instead of active editor?
    workspace.onDidSaveTextDocument((_) => {
        if (focusMode) {
            computeDependenciesRequest();
        }
    });

    // On single word selection (in lieu of double click): Get slice corresponding to the selected word (if it is a variable)
    vscode.window.onDidChangeTextEditorSelection(event => {
        if (!focusMode) {return;} // Only proceed if focus mode is enabled

        const editor = event.textEditor;
        const selection = editor.selection;

        // Check if exactly one word is selected
        if (!selection.isEmpty) {
            const wordRange = editor.document.getWordRangeAtPosition(selection.start);
            if (wordRange) {
                const word = editor.document.getText(wordRange);
                const params = {
                    uri: editor.document.uri.toString(),
                    word: word,
                    // TODO: The adjustment shouldn't be happening here.
                    position: { line: selection.start.line + 1, character: selection.start.character + 1 }
                };

                client.sendRequest("workspace/executeCommand", {
                    command: "computeSlice",
                    arguments: [params]
                });
            }
        }
    });

    // Start server that provides Guppy language services.
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

// Deactivate the server.
export function deactivate() {
    if (!client) {
		return undefined;
	}
	return client.stop();
}
