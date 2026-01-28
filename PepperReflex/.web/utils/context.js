import { createContext, useContext, useMemo, useReducer, useState, createElement, useEffect } from "react"
import { applyDelta, ReflexEvent, hydrateClientStorage, useEventLoop, refs } from "$/utils/state"
import { jsx } from "@emotion/react";

export const initialState = {"reflex___state____state": {"is_hydrated_rx_state_": false, "router_rx_state_": {"session": {"client_token": "", "client_ip": "", "session_id": ""}, "headers": {"host": "", "origin": "", "upgrade": "", "connection": "", "cookie": "", "pragma": "", "cache_control": "", "user_agent": "", "sec_websocket_version": "", "sec_websocket_key": "", "sec_websocket_extensions": "", "accept_encoding": "", "accept_language": "", "raw_headers": {}}, "page": {"host": "", "path": "", "raw_path": "", "full_path": "", "full_raw_path": "", "params": {}}, "url": "", "route_id": ""}}, "reflex___state____state.pepper_reflex___state____base_state": {"autorun_status_rx_state_": "Idle", "cards_display_rx_state_": "flex", "cards_header_color_rx_state_": "#e0e8f7", "cards_ratio_rx_state_": 1.0, "chat_display_rx_state_": "flex", "chat_header_color_rx_state_": "#b6e3b6", "chat_ratio_rx_state_": 1.0, "control_service_status_rx_state_": "Unknown", "diagnostics_text_rx_state_": "Control service: Unknown\nControl status: Ready\nActive model: None\nLast poll: -\nAutorun: Idle", "grid_template_columns_rx_state_": "1fr 1fr 1fr", "last_poll_ts_rx_state_": "", "layout_preset_rx_state_": "Equal", "model_name_rx_state_": "None", "model_options_rx_state_": ["Loading..."], "model_ready_rx_state_": true, "model_state_rx_state_": "Ready", "polling_active_rx_state_": true, "progress_rx_state_": 50, "progress_value_rx_state_": 50, "selected_model_rx_state_": "Loading...", "settings_display_rx_state_": "flex", "settings_header_color_rx_state_": "#b6e3b6", "settings_ratio_rx_state_": 1.0, "show_cards_rx_state_": true, "show_chat_rx_state_": true, "show_settings_rx_state_": true, "status_text_rx_state_": "", "toggle_cards_color_rx_state_": "#cfe8ff", "toggle_chat_color_rx_state_": "#cfe8ff", "toggle_settings_color_rx_state_": "#cfe8ff"}, "reflex___state____state.pepper_reflex___state____base_state.pepper_reflex___state____cards_state": {"cards_rx_state_": ["Card 01", "Card 02", "Card 03", "Card 04", "Card 05", "Card 06"]}, "reflex___state____state.pepper_reflex___state____base_state.pepper_reflex___state____chat_state": {"autorun_loaded_rx_state_": false, "input_text_rx_state_": "", "messages_rx_state_": [{"role": "assistant", "text": "Welcome to ChatLlama (Reflex UI demo)."}, {"role": "user", "text": "Show me the model status and tools."}, {"role": "assistant", "text": "Model: Ready. Tools: internal SVG cards enabled."}]}, "reflex___state____state.pepper_reflex___state____base_state.pepper_reflex___state____settings_state": {"built_in_mcps_rx_state_": [{"name": "svg_card", "enabled": true, "methods": ["CreateCard", "DrawCard", "DeleteCard"]}, {"name": "mcp_card_textviewer", "enabled": true, "methods": ["CreateCard", "DrawCard"]}], "mcp_items_rx_state_": [{"name": "internal", "enabled": true, "transport": "stdio", "url": "", "port": ""}, {"name": "fashion_http", "enabled": false, "transport": "http", "url": "http://localhost", "port": "8014"}]}, "reflex___state____state.reflex___state____frontend_event_exception_state": {}, "reflex___state____state.reflex___state____on_load_internal_state": {}, "reflex___state____state.reflex___state____update_vars_internal_state": {}}

export const defaultColorMode = "system"
export const ColorModeContext = createContext(null);
export const UploadFilesContext = createContext(null);
export const DispatchContext = createContext(null);
export const StateContexts = {reflex___state____state: createContext(null),reflex___state____state__pepper_reflex___state____base_state: createContext(null),reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____cards_state: createContext(null),reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____chat_state: createContext(null),reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____settings_state: createContext(null),reflex___state____state__reflex___state____frontend_event_exception_state: createContext(null),reflex___state____state__reflex___state____on_load_internal_state: createContext(null),reflex___state____state__reflex___state____update_vars_internal_state: createContext(null),};
export const EventLoopContext = createContext(null);
export const clientStorage = {"cookies": {}, "local_storage": {}, "session_storage": {}}


export const state_name = "reflex___state____state"

export const exception_state_name = "reflex___state____state.reflex___state____frontend_event_exception_state"

// These events are triggered on initial load and each page navigation.
export const onLoadInternalEvent = () => {
    const internal_events = [];

    // Get tracked cookie and local storage vars to send to the backend.
    const client_storage_vars = hydrateClientStorage(clientStorage);
    // But only send the vars if any are actually set in the browser.
    if (client_storage_vars && Object.keys(client_storage_vars).length !== 0) {
        internal_events.push(
            ReflexEvent(
                'reflex___state____state.reflex___state____update_vars_internal_state.update_vars_internal',
                {vars: client_storage_vars},
            ),
        );
    }

    // `on_load_internal` triggers the correct on_load event(s) for the current page.
    // If the page does not define any on_load event, this will just set `is_hydrated = true`.
    internal_events.push(ReflexEvent('reflex___state____state.reflex___state____on_load_internal_state.on_load_internal'));

    return internal_events;
}

// The following events are sent when the websocket connects or reconnects.
export const initialEvents = () => [
    ReflexEvent('reflex___state____state.hydrate'),
    ...onLoadInternalEvent()
]
    

export const isDevMode = true;

export function UploadFilesProvider({ children }) {
  const [filesById, setFilesById] = useState({})
  refs["__clear_selected_files"] = (id) => setFilesById(filesById => {
    const newFilesById = {...filesById}
    delete newFilesById[id]
    return newFilesById
  })
  return createElement(
    UploadFilesContext.Provider,
    { value: [filesById, setFilesById] },
    children
  );
}

export function ClientSide(component) {
  return ({ children, ...props }) => {
    const [Component, setComponent] = useState(null);
    useEffect(() => {
      async function load() {
        const comp = await component();
        setComponent(() => comp);
      }
      load();
    }, []);
    return Component ? jsx(Component, props, children) : null;
  };
}

export function EventLoopProvider({ children }) {
  const dispatch = useContext(DispatchContext)
  const [addEvents, connectErrors] = useEventLoop(
    dispatch,
    initialEvents,
    clientStorage,
  )
  return createElement(
    EventLoopContext.Provider,
    { value: [addEvents, connectErrors] },
    children
  );
}

export function StateProvider({ children }) {
  const [reflex___state____state, dispatch_reflex___state____state] = useReducer(applyDelta, initialState["reflex___state____state"])
const [reflex___state____state__pepper_reflex___state____base_state, dispatch_reflex___state____state__pepper_reflex___state____base_state] = useReducer(applyDelta, initialState["reflex___state____state.pepper_reflex___state____base_state"])
const [reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____cards_state, dispatch_reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____cards_state] = useReducer(applyDelta, initialState["reflex___state____state.pepper_reflex___state____base_state.pepper_reflex___state____cards_state"])
const [reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____chat_state, dispatch_reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____chat_state] = useReducer(applyDelta, initialState["reflex___state____state.pepper_reflex___state____base_state.pepper_reflex___state____chat_state"])
const [reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____settings_state, dispatch_reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____settings_state] = useReducer(applyDelta, initialState["reflex___state____state.pepper_reflex___state____base_state.pepper_reflex___state____settings_state"])
const [reflex___state____state__reflex___state____frontend_event_exception_state, dispatch_reflex___state____state__reflex___state____frontend_event_exception_state] = useReducer(applyDelta, initialState["reflex___state____state.reflex___state____frontend_event_exception_state"])
const [reflex___state____state__reflex___state____on_load_internal_state, dispatch_reflex___state____state__reflex___state____on_load_internal_state] = useReducer(applyDelta, initialState["reflex___state____state.reflex___state____on_load_internal_state"])
const [reflex___state____state__reflex___state____update_vars_internal_state, dispatch_reflex___state____state__reflex___state____update_vars_internal_state] = useReducer(applyDelta, initialState["reflex___state____state.reflex___state____update_vars_internal_state"])
  const dispatchers = useMemo(() => {
    return {
      "reflex___state____state": dispatch_reflex___state____state,
"reflex___state____state.pepper_reflex___state____base_state": dispatch_reflex___state____state__pepper_reflex___state____base_state,
"reflex___state____state.pepper_reflex___state____base_state.pepper_reflex___state____cards_state": dispatch_reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____cards_state,
"reflex___state____state.pepper_reflex___state____base_state.pepper_reflex___state____chat_state": dispatch_reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____chat_state,
"reflex___state____state.pepper_reflex___state____base_state.pepper_reflex___state____settings_state": dispatch_reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____settings_state,
"reflex___state____state.reflex___state____frontend_event_exception_state": dispatch_reflex___state____state__reflex___state____frontend_event_exception_state,
"reflex___state____state.reflex___state____on_load_internal_state": dispatch_reflex___state____state__reflex___state____on_load_internal_state,
"reflex___state____state.reflex___state____update_vars_internal_state": dispatch_reflex___state____state__reflex___state____update_vars_internal_state,
    }
  }, [])

  return (
    createElement(StateContexts.reflex___state____state,{value: reflex___state____state},
createElement(StateContexts.reflex___state____state__pepper_reflex___state____base_state,{value: reflex___state____state__pepper_reflex___state____base_state},
createElement(StateContexts.reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____cards_state,{value: reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____cards_state},
createElement(StateContexts.reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____chat_state,{value: reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____chat_state},
createElement(StateContexts.reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____settings_state,{value: reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____settings_state},
createElement(StateContexts.reflex___state____state__reflex___state____frontend_event_exception_state,{value: reflex___state____state__reflex___state____frontend_event_exception_state},
createElement(StateContexts.reflex___state____state__reflex___state____on_load_internal_state,{value: reflex___state____state__reflex___state____on_load_internal_state},
createElement(StateContexts.reflex___state____state__reflex___state____update_vars_internal_state,{value: reflex___state____state__reflex___state____update_vars_internal_state},
    createElement(DispatchContext, {value: dispatchers}, children)
    ))))))))
  )
}