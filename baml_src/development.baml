client DevelopmentDefault = openai.ChatClient.new(capture_wire = false);

class DevelopmentJevResponse { model: string, answers: map<string, typesafe_patch.internal.Answer>, usage: typesafe_patch.internal.Usage? }
function development_judgment_decode(body: string, model: string) -> bool {
    let response = baml.json.from_string<DevelopmentJevResponse>(body);
    if (response.model != model) { throw typesafe_patch.internal.failed("Development JEV response model mismatch") }
    let answer: typesafe_patch.internal.Answer = response.answers.get("result") else { throw typesafe_patch.internal.failed("Missing development JEV answer") };
    let probability: float = answer.noul else { throw typesafe_patch.internal.failed("Missing development JEV probability") };
    if (answer.type != "noul" || probability < 0.0 || probability > 1.0) { throw typesafe_patch.internal.failed("Invalid development JEV probability") }
    probability >= 0.5
}
function development_task_request_shape(task: string, offered: string, model: string) -> string {
    IsSuitable@spec(task, offered).build_request(client = typesafeai.Client.new(model = model, api_key = "preview", capture_wire = false)).body
}

function development_discovery_request_shape(task: string, offered: string, model: string) -> string {
    DiscoveryOptionSuitable@spec(task, offered).build_request(client = typesafeai.Client.new(model = model, api_key = "preview", capture_wire = false)).body
}
function development_discovery_judgment(task: string, offered: string, model: string, api_key: string, base_url: string, timeout_ms: int, on_event: ((JevUsageObservation) -> void)?) -> bool {
    let cl = typesafe_patch.Client.new(model = model, api_key = api_key, base_url = base_url, request_timeout_ms = timeout_ms, capture_wire = false);
    let spec = DiscoveryOptionSuitable@spec(task, offered);
    let turn = typesafe_patch.internal.observe(cl, ai.ModelTurnInput {
        prompt: spec.prompt_template, journal: ai.Journal.new(spec), toolbox: spec.tools(), output_type: spec.output_type()
    }, on_event);
    match (turn.content[0]) { let text: ai.content.Text => spec.parse(text.text), _ => throw typesafe_patch.internal.failed("Invalid JEV content") }
}
function development_task_judgment(task: string, offered: string, model: string, api_key: string, base_url: string, timeout_ms: int, on_event: ((JevUsageObservation) -> void)?) -> bool {
    let cl = typesafe_patch.Client.new(model = model, api_key = api_key, base_url = base_url, request_timeout_ms = timeout_ms, capture_wire = false);
    let spec = IsSuitable@spec(task, offered);
    let turn = typesafe_patch.internal.observe(cl, ai.ModelTurnInput {
        prompt: spec.prompt_template, journal: ai.Journal.new(spec), toolbox: spec.tools(), output_type: spec.output_type()
    }, on_event);
    match (turn.content[0]) { let text: ai.content.Text => spec.parse(text.text), _ => throw typesafe_patch.internal.failed("Invalid JEV content") }
}

function DevelopmentText(task: string) -> string {
    client: DevelopmentDefault
    prompt: `${role("system")}Complete the development task. Return only JavaScript defining solve, without Markdown fences. ${role("user")}${task}`
}

function development_client(model: string, api_key: string, base_url: string, timeout_ms: int, output_tokens: int, observe_wire: bool = false) -> openai.ChatClient {
    openai.ChatClient.new(
        model = model, api_key = api_key, base_url = base_url,
        request_timeout_ms = timeout_ms, max_completion_tokens = output_tokens,
        request_body = baml.json.parse("{\"n\":1,\"store\":false,\"service_tier\":\"default\"}"),
        capture_wire = observe_wire
    )
}

function development_request_shape(task: string, model: string, output_tokens: int) -> string {
    DevelopmentText@spec(task).build_request(client = development_client(model, "preview", "https://api.openai.com/v1", 1000, output_tokens)).body
}

function development_completion(task: string, model: string, api_key: string, base_url: string, timeout_ms: int, output_tokens: int) -> ai.ModelTurn {
    let spec = DevelopmentText@spec(task);
    let cl = development_client(model, api_key, base_url, timeout_ms, output_tokens);
    cl.invoke(ai.ModelTurnInput {
        prompt: spec.prompt_template,
        journal: ai.Journal.new(spec),
        toolbox: spec.tools(),
        output_type: spec.output_type()
    })
}

function development_observed_completion(task: string, model: string, api_key: string, base_url: string, timeout_ms: int, output_tokens: int, family: string) -> ai.ModelTurn {
    let cl = development_client(model, api_key, base_url, timeout_ms, output_tokens, observe_wire = true);
    if (family == "implementation") {
        let spec = DevelopmentText@spec(task);
        return cl.invoke(ai.ModelTurnInput { prompt: spec.prompt_template, journal: ai.Journal.new(spec), toolbox: spec.tools(), output_type: spec.output_type() });
    }
    let spec = DevelopmentArtifactText@spec(task);
    cl.invoke(ai.ModelTurnInput { prompt: spec.prompt_template, journal: ai.Journal.new(spec), toolbox: spec.tools(), output_type: spec.output_type() })
}

function DevelopmentArtifactText(task: string) -> string {
    client: DevelopmentDefault
    prompt: `${role("system")}Complete the development task. Return only the requested structured answer, without Markdown fences. ${role("user")}${task}`
}

function development_artifact_request_shape(task: string, model: string, output_tokens: int) -> string {
    DevelopmentArtifactText@spec(task).build_request(client = development_client(model, "preview", "https://api.openai.com/v1", 1000, output_tokens)).body
}

function development_artifact_completion(task: string, model: string, api_key: string, base_url: string, timeout_ms: int, output_tokens: int) -> ai.ModelTurn {
    let spec = DevelopmentArtifactText@spec(task);
    let cl = development_client(model, api_key, base_url, timeout_ms, output_tokens);
    cl.invoke(ai.ModelTurnInput {
        prompt: spec.prompt_template, journal: ai.Journal.new(spec),
        toolbox: spec.tools(), output_type: spec.output_type()
    })
}

function LocalDevelopmentText(task: string) -> string {
    client: DevelopmentDefault
    prompt: `${role("system")}Complete the development task. Return only the requested answer, without Markdown fences. ${role("user")}${task}`
}

function local_development_client(model: string, base_url: string, timeout_ms: int, output_tokens: int, options_json: string) -> openai.ChatClient {
    openai.ChatClient.new(
        model = model, api_key = "local-only", base_url = base_url,
        request_timeout_ms = timeout_ms, max_completion_tokens = output_tokens,
        request_body = baml.json.parse(options_json), capture_wire = true
    )
}

function local_development_request_shape(task: string, model: string, output_tokens: int, options_json: string) -> string {
    LocalDevelopmentText@spec(task).build_request(client = local_development_client(model, "http://127.0.0.1:8002/v1", 1000, output_tokens, options_json)).body
}

function local_development_completion(task: string, model: string, base_url: string, timeout_ms: int, output_tokens: int, options_json: string) -> ai.ModelTurn {
    let spec = LocalDevelopmentText@spec(task);
    let cl = local_development_client(model, base_url, timeout_ms, output_tokens, options_json);
    cl.invoke(ai.ModelTurnInput {
        prompt: spec.prompt_template, journal: ai.Journal.new(spec),
        toolbox: spec.tools(), output_type: spec.output_type()
    })
}
