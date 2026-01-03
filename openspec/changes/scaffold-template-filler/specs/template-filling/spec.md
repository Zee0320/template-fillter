# Spec: Template Filling

## ADDED Requirements

#### Scenario: Fill simple text placeholder
Given a Word document with "Hello {{NAME}}"
And a context "The user is Alice"
And a schema mapping "NAME" to "Extract name from context"
When the tool is run
Then the output document contains "Hello Alice"
And the text "Alice" retains the formatting of "{{NAME}}"

#### Scenario: Fill multiple placeholders
Given a Word document with "{{TITLE}}" and "{{SUMMARY}}"
And a context text
And a corresponding schema
When the tool is run
Then both placeholders are replaced with relevant generated text

#### Scenario: Handle missing context
Given a placeholder requires info not in context
When the tool is run
Then the placeholder should ideally be filled with a placeholder message or logic to handle uncertainty (configurable)

#### Scenario: Preserve Formatting
Given a placeholder "{{BOLD}}" is bold and red
When it is replaced
Then the new text is bold and red
