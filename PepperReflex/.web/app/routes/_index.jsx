import {Fragment,useCallback,useContext,useEffect,useRef} from "react"
import {Box as RadixThemesBox,Button as RadixThemesButton,Card as RadixThemesCard,Flex as RadixThemesFlex,Progress as RadixThemesProgress,Select as RadixThemesSelect,Text as RadixThemesText,TextArea as RadixThemesTextArea,TextField as RadixThemesTextField,Theme as RadixThemesTheme} from "@radix-ui/themes"
import theme from "$/utils/theme"
import {EventLoopContext,StateContexts} from "$/utils/context"
import {ReflexEvent,isNotNullOrUndefined,isTrue,refs} from "$/utils/state"
import {Panel as ResizablePanel,PanelGroup as ResizablePanelGroup,PanelResizeHandle as ResizablePanelResizeHandle} from "react-resizable-panels"
import {Content as RadixAccordionContent,Header as RadixAccordionHeader,Item as RadixAccordionItem,Root as RadixAccordionRoot,Trigger as RadixAccordionTrigger} from "@radix-ui/react-accordion"
import {jsx,keyframes} from "@emotion/react"
import DebounceInput from "react-debounce-input"




function Fragment_c0a0b3abf1673d25f69e0fd63bb8027a () {
  const [addEvents, connectErrors] = useContext(EventLoopContext);
const on_before_unload_d8c89e8d83238df504447b44dc635666 = useCallback(((...args) => (addEvents([(ReflexEvent("reflex___state____state.pepper_reflex___state____base_state.on_before_unload", ({  }), ({  })))], args, ({  })))), [addEvents, ReflexEvent])
const on_before_unload_be22f5ae36b477d3f2cf556a72c45dfe = useCallback(on_before_unload_d8c89e8d83238df504447b44dc635666, [addEvents, ReflexEvent])

useEffect(() => {
    if (typeof window === 'undefined') return;
    const fn = on_before_unload_be22f5ae36b477d3f2cf556a72c45dfe;
    window.addEventListener('beforeunload', fn);
    return () => window.removeEventListener('beforeunload', fn);
}, []);
                
  return (
    jsx(Fragment,{},)
  )
}


function Text_c6e1519036d25527b1b79be76683551b () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(RadixThemesText,{as:"p"},"Model: ",reflex___state____state__pepper_reflex___state____base_state.model_name_rx_state_)
  )
}


function Fragment_498f8c69dd34716005332c2269185b1d () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(Fragment,{},((reflex___state____state__pepper_reflex___state____base_state.model_name_rx_state_?.valueOf?.() === "None"?.valueOf?.())?(jsx(Fragment,{},"Model: None")):(jsx(Fragment,{},jsx(Text_c6e1519036d25527b1b79be76683551b,{},)))))
  )
}


function Text_dfbdefd3c75647074d62ea5c75d930da () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(RadixThemesText,{as:"p",css:({ ["fontSize"] : "0.8rem", ["color"] : "#adb5bd" })},reflex___state____state__pepper_reflex___state____base_state.status_text_rx_state_)
  )
}


function Progress_0c62b0acefcf110a865e6b4de6f811de () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(RadixThemesProgress,{color:"teal",css:({ ["width"] : "150px", ["position"] : "relative" }),value:reflex___state____state__pepper_reflex___state____base_state.progress_value_rx_state_},)
  )
}


function Button_a5b424af077f0e7d8fbbe467a9827eb8 () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)
const [addEvents, connectErrors] = useContext(EventLoopContext);

const on_click_0e4ac3bf8616d9f47d9fb89b01701233 = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.pepper_reflex___state____base_state.toggle_settings", ({  }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])

  return (
    jsx(RadixThemesButton,{css:({ ["backgroundColor"] : (reflex___state____state__pepper_reflex___state____base_state.show_settings_rx_state_ ? "#63e6be" : "transparent"), ["color"] : (reflex___state____state__pepper_reflex___state____base_state.show_settings_rx_state_ ? "#1a1b1e" : "#e9ecef"), ["border"] : (reflex___state____state__pepper_reflex___state____base_state.show_settings_rx_state_ ? "1px solid #63e6be" : "1px solid #373a40"), ["borderRadius"] : "2px" }),onClick:on_click_0e4ac3bf8616d9f47d9fb89b01701233,size:"2"},"Settings")
  )
}


function Button_51f532c4831f34e9349288686fba0557 () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)
const [addEvents, connectErrors] = useContext(EventLoopContext);

const on_click_4cea4998818c67dc88f776073595f511 = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.pepper_reflex___state____base_state.toggle_chat", ({  }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])

  return (
    jsx(RadixThemesButton,{css:({ ["backgroundColor"] : (reflex___state____state__pepper_reflex___state____base_state.show_chat_rx_state_ ? "#63e6be" : "transparent"), ["color"] : (reflex___state____state__pepper_reflex___state____base_state.show_chat_rx_state_ ? "#1a1b1e" : "#e9ecef"), ["border"] : (reflex___state____state__pepper_reflex___state____base_state.show_chat_rx_state_ ? "1px solid #63e6be" : "1px solid #373a40"), ["borderRadius"] : "2px" }),onClick:on_click_4cea4998818c67dc88f776073595f511,size:"2"},"Chat")
  )
}


function Button_876b0f2b9bc2c7944ef8069078c5f53f () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)
const [addEvents, connectErrors] = useContext(EventLoopContext);

const on_click_e1d6b0eb8fba0bd001e9afefe2600fad = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.pepper_reflex___state____base_state.toggle_cards", ({  }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])

  return (
    jsx(RadixThemesButton,{css:({ ["backgroundColor"] : (reflex___state____state__pepper_reflex___state____base_state.show_cards_rx_state_ ? "#63e6be" : "transparent"), ["color"] : (reflex___state____state__pepper_reflex___state____base_state.show_cards_rx_state_ ? "#1a1b1e" : "#e9ecef"), ["border"] : (reflex___state____state__pepper_reflex___state____base_state.show_cards_rx_state_ ? "1px solid #63e6be" : "1px solid #373a40"), ["borderRadius"] : "2px" }),onClick:on_click_e1d6b0eb8fba0bd001e9afefe2600fad,size:"2"},"Cards")
  )
}


function Text_499af9570b2efb4ebad6d9423e9d15a9 () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(RadixThemesText,{as:"p",css:({ ["color"] : (reflex___state____state__pepper_reflex___state____base_state.model_ready_rx_state_ ? "#1c7c1c" : "#adb5bd"), ["fontWeight"] : "bold" })},"Model: ",reflex___state____state__pepper_reflex___state____base_state.selected_model_rx_state_)
  )
}


function Select__group_797a07f9a61c27ef77dca65c2e7d796d () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(RadixThemesSelect.Group,{},"",Array.prototype.map.call(reflex___state____state__pepper_reflex___state____base_state.model_options_rx_state_ ?? [],((item_rx_state_,index_9823cf83aa70cfbb1602bac35e8f2f1e)=>(jsx(RadixThemesSelect.Item,{key:index_9823cf83aa70cfbb1602bac35e8f2f1e,value:item_rx_state_},item_rx_state_)))))
  )
}


function Select__root_ad027a400360796b695bb14958551772 () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)
const [addEvents, connectErrors] = useContext(EventLoopContext);

const on_change_6a9fc26e3304e4c5e22ffac90419e9c9 = useCallback(((_ev_0) => (addEvents([(ReflexEvent("reflex___state____state.pepper_reflex___state____base_state.set_selected_model", ({ ["value"] : _ev_0 }), ({  })))], [_ev_0], ({  })))), [addEvents, ReflexEvent])

  return (
    jsx(RadixThemesSelect.Root,{css:({ ["flex"] : "1" }),onValueChange:on_change_6a9fc26e3304e4c5e22ffac90419e9c9,value:reflex___state____state__pepper_reflex___state____base_state.selected_model_rx_state_},jsx(RadixThemesSelect.Trigger,{placeholder:"Select a model"},),jsx(RadixThemesSelect.Content,{},jsx(Select__group_797a07f9a61c27ef77dca65c2e7d796d,{},)))
  )
}


function Button_cadca0cbd91512a210730cce4d71cfb2 () {
  const [addEvents, connectErrors] = useContext(EventLoopContext);

const on_click_1689a1b8fb20a3eb6d511fe1d9ef994a = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.pepper_reflex___state____base_state.load_model", ({  }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])

  return (
    jsx(RadixThemesButton,{color:"blue",css:({ ["width"] : "auto", ["flexShrink"] : "0" }),onClick:on_click_1689a1b8fb20a3eb6d511fe1d9ef994a,size:"2",variant:"solid"},"Load")
  )
}


function Flex_f5cf1ad59b80b4631a48389004c2814c () {
  const reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____settings_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____settings_state)
const [addEvents, connectErrors] = useContext(EventLoopContext);



  return (
    jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%" }),direction:"column",gap:"3"},Array.prototype.map.call(reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____settings_state.mcp_items_rx_state_ ?? [],((item_rx_state_,index_e373a016f9a9e3ff5b282d63915e392e)=>(jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%" }),direction:"column",key:index_e373a016f9a9e3ff5b282d63915e392e,gap:"2"},jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%" }),direction:"row",gap:"2"},jsx(RadixThemesButton,{color:(item_rx_state_?.["enabled"] ? "green" : "red"),onClick:((_e) => (addEvents([(ReflexEvent("reflex___state____state.pepper_reflex___state____base_state.pepper_reflex___state____settings_state.toggle_mcp", ({ ["name"] : item_rx_state_?.["name"] }), ({  })))], [_e], ({  })))),size:"1"},(item_rx_state_?.["enabled"] ? "\u2713" : "\u2717")),jsx(RadixThemesText,{as:"p",css:({ ["fontWeight"] : "bold" })},item_rx_state_?.["name"]),jsx(RadixThemesFlex,{css:({ ["flex"] : 1, ["justifySelf"] : "stretch", ["alignSelf"] : "stretch" })},),jsx(RadixThemesButton,{onClick:((_e) => (addEvents([(ReflexEvent("reflex___state____state.pepper_reflex___state____base_state.pepper_reflex___state____settings_state.delete_mcp", ({  }), ({  })))], [_e], ({  }))))},"\u2715")),jsx(Fragment,{},((item_rx_state_?.["transport"]?.valueOf?.() === "http"?.valueOf?.())?(jsx(Fragment,{},jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%" }),direction:"row",gap:"2"},jsx(RadixThemesTextField.Root,{css:({ ["width"] : "70%" }),placeholder:"URL",value:(isNotNullOrUndefined(item_rx_state_?.["url"]) ? item_rx_state_?.["url"] : "")},),jsx(RadixThemesTextField.Root,{css:({ ["width"] : "30%" }),placeholder:"PORT",value:(isNotNullOrUndefined(item_rx_state_?.["port"]) ? item_rx_state_?.["port"] : "")},)))):(jsx(Fragment,{},)))))))))
  )
}


function Flex_c482eb1a15f8211eedc6c960b90b89bc () {
  const reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____settings_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____settings_state)
const [addEvents, connectErrors] = useContext(EventLoopContext);



  return (
    jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%" }),direction:"column",gap:"3"},Array.prototype.map.call(reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____settings_state.built_in_mcps_rx_state_ ?? [],((item_rx_state_,index_f322d8281ea1bdfd4f20b6c1571a4f08)=>(jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%" }),direction:"column",key:index_f322d8281ea1bdfd4f20b6c1571a4f08,gap:"2"},jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%" }),direction:"row",gap:"2"},jsx(RadixThemesButton,{color:(item_rx_state_?.["enabled"] ? "green" : "red"),onClick:((_e) => (addEvents([(ReflexEvent("reflex___state____state.pepper_reflex___state____base_state.pepper_reflex___state____settings_state.toggle_built_in_mcp", ({ ["name"] : item_rx_state_?.["name"] }), ({  })))], [_e], ({  })))),size:"1"},(item_rx_state_?.["enabled"] ? "\u2713" : "\u2717")),jsx(RadixThemesText,{as:"p",css:({ ["fontWeight"] : "bold" })},item_rx_state_?.["name"])),jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",direction:"row",gap:"2",wrap:"wrap"},Array.prototype.map.call(item_rx_state_?.["methods"] ?? [],((method_rx_state_,index_9277f282ec774ad68eb56e80c504a3ab)=>(jsx(RadixThemesBox,{css:({ ["padding"] : "2px 6px", ["border"] : "1px solid #999", ["backgroundColor"] : "#1f2329", ["borderRadius"] : "4px" }),key:index_9277f282ec774ad68eb56e80c504a3ab},jsx(RadixThemesText,{as:"p",css:({ ["fontSize"] : "0.8rem" })},method_rx_state_)))))))))))
  )
}


function Trigger_66247fc47dcba02740b522ecd3bfd144 () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)
const [addEvents, connectErrors] = useContext(EventLoopContext);



  return (
    jsx(RadixAccordionTrigger,{className:"AccordionTrigger",css:({ ["color"] : "#e9ecef", ["fontSize"] : "1.1em", ["lineHeight"] : 1, ["justifyContent"] : "space-between", ["alignItems"] : "center", ["flex"] : 1, ["display"] : "flex", ["padding"] : "10px", ["width"] : "100%", ["boxShadow"] : "0 var(--divider-px) 0 var(--gray-a6)", ["&[data-state='open'] > .AccordionChevron"] : ({ ["transform"] : "rotate(180deg)" }), ["&:hover"] : ({ ["backgroundColor"] : "#373a40" }), ["& > .AccordionChevron"] : ({ ["transition"] : "transform var(--animation-duration) var(--animation-easing)" }), ["&[data-variant='classic'], *:where([data-variant='classic']) &"] : ({ ["color"] : "var(--accent-contrast)", ["&:hover"] : ({ ["backgroundColor"] : "var(--accent-10)" }), ["& > .AccordionChevron"] : ({ ["color"] : "var(--accent-contrast)" }) }), ["background"] : "none", ["border"] : "none", ["backgroundColor"] : "#2c2e33", ["fontWeight"] : "bold", ["textAlign"] : "left" })},jsx(RadixThemesFlex,{align:"center",className:"rx-Stack",css:({ ["width"] : "100%" }),direction:"row",gap:"3"},jsx(RadixThemesText,{as:"p"},"Diagnostics"),jsx(RadixThemesFlex,{css:({ ["flex"] : 1, ["justifySelf"] : "stretch", ["alignSelf"] : "stretch" })},),jsx(RadixThemesButton,{onClick:((_e) => (addEvents([(ReflexEvent("_call_function", ({ ["function"] : (() => (navigator?.["clipboard"]?.["writeText"](reflex___state____state__pepper_reflex___state____base_state.diagnostics_text_rx_state_))), ["callback"] : null }), ({  }))), (ReflexEvent("_call_function", ({ ["function"] : (() => null), ["callback"] : null }), ({ ["stopPropagation"] : true })))], [_e], ({  })))),size:"1",variant:"soft"},"Copy all")))
  )
}


function Text_242f86d24710c0f8ec0f610c5d56ee95 () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(RadixThemesText,{as:"p",css:({ ["color"] : "#adb5bd" })},"Control service: ",reflex___state____state__pepper_reflex___state____base_state.control_service_status_rx_state_)
  )
}


function Text_9205caafe22c707e74f27adda3dfc04e () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(RadixThemesText,{as:"p",css:({ ["color"] : "#adb5bd" })},"Control status: ",reflex___state____state__pepper_reflex___state____base_state.model_state_rx_state_)
  )
}


function Text_c1707882608b8d057d06458a64b4e33c () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(RadixThemesText,{as:"p",css:({ ["color"] : "#adb5bd" })},"Active model: ",reflex___state____state__pepper_reflex___state____base_state.model_name_rx_state_)
  )
}


function Text_63e7450d9174018faf1af5865840d6eb () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(RadixThemesText,{as:"p",css:({ ["color"] : "#adb5bd" })},"Last poll: ",(!((reflex___state____state__pepper_reflex___state____base_state.last_poll_ts_rx_state_?.valueOf?.() === ""?.valueOf?.())) ? reflex___state____state__pepper_reflex___state____base_state.last_poll_ts_rx_state_ : "-"))
  )
}


function Text_0ae37c0d7e84d43257464e2c2a3ac115 () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(RadixThemesText,{as:"p",css:({ ["color"] : "#adb5bd" })},"Autorun: ",reflex___state____state__pepper_reflex___state____base_state.autorun_status_rx_state_)
  )
}


function Fragment_e910531d68efb7757da93546d7f2461a () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(Fragment,{},(reflex___state____state__pepper_reflex___state____base_state.show_settings_rx_state_?(jsx(Fragment,{},jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["height"] : "100%", ["flex"] : "1" }),direction:"column",gap:"0"},jsx(RadixThemesBox,{css:({ ["padding"] : "6px 10px", ["backgroundColor"] : "#2c2e33", ["borderBottom"] : "1px solid #373a40", ["color"] : "#e9ecef", ["fontWeight"] : "bold", ["fontFamily"] : "Inter, 'Segoe UI', sans-serif", ["--default-font-family"] : "Inter, 'Segoe UI', sans-serif", ["width"] : "100%" })},jsx(RadixThemesText,{as:"p",css:({ ["fontWeight"] : "bold" })},"Settings")),jsx(RadixThemesBox,{css:({ ["overflowY"] : "auto", ["flex"] : "1", ["width"] : "100%" })},jsx(RadixThemesBox,{css:({ ["border"] : "1px solid #373a40", ["borderRadius"] : "8px", ["margin"] : "8px", ["backgroundColor"] : "#25262b", ["overflow"] : "auto" })},jsx(RadixAccordionRoot,{collapsible:true,css:({ ["borderRadius"] : "var(--radius-4)", ["boxShadow"] : "0 2px 10px var(--black-a1)", ["&[data-variant='classic']"] : ({ ["backgroundColor"] : "var(--accent-9)", ["boxShadow"] : "0 2px 10px var(--black-a4)" }), ["&[data-variant='soft']"] : ({ ["backgroundColor"] : "var(--accent-3)" }), ["&[data-variant='outline']"] : ({ ["border"] : "1px solid var(--accent-6)", ["--divider-px"] : "1px" }), ["&[data-variant='surface']"] : ({ ["border"] : "1px solid var(--accent-6)", ["backgroundColor"] : "var(--accent-surface)", ["--divider-px"] : "1px" }), ["&[data-variant='ghost']"] : ({ ["backgroundColor"] : "none", ["boxShadow"] : "None" }), ["--animation-duration"] : (250+"ms"), ["--animation-easing"] : "cubic-bezier(0.87, 0, 0.13, 1)", ["width"] : "100%" }),"data-variant":"soft",type:"multiple"},jsx(RadixAccordionItem,{className:"AccordionItem",css:({ ["overflow"] : "hidden", ["width"] : "100%", ["marginTop"] : "1px", ["borderTop"] : "var(--divider-px) solid var(--gray-a6)", ["&:first-child"] : ({ ["marginTop"] : 0, ["borderTop"] : 0, ["borderTopLeftRadius"] : "var(--radius-4)", ["borderTopRightRadius"] : "var(--radius-4)" }), ["&:last-child"] : ({ ["borderBottomLeftRadius"] : "var(--radius-4)", ["borderBottomRightRadius"] : "var(--radius-4)" }), ["&:focus-within"] : ({ ["position"] : "relative", ["zIndex"] : 1 }), ["&:first-child[data-variant='ghost'], *:where([data-variant='ghost']) &:first-child"] : ({ ["borderRadius"] : 0, ["borderTop"] : "var(--divider-px) solid var(--gray-a6)" }), ["&:last-child[data-variant='ghost'], *:where([data-variant='ghost']) &:last-child"] : ({ ["borderRadius"] : 0, ["borderBottom"] : "var(--divider-px) solid var(--gray-a6)" }), ["border"] : "1px solid #373a40", ["backgroundColor"] : "#25262b", ["marginBottom"] : "8px", ["borderRadius"] : "8px", ["paddingBottom"] : "2em" }),value:"models"},jsx(RadixAccordionHeader,{className:"AccordionHeader",css:({ ["display"] : "flex", ["margin"] : "0" })},jsx(RadixAccordionTrigger,{className:"AccordionTrigger",css:({ ["color"] : "#e9ecef", ["fontSize"] : "1.1em", ["lineHeight"] : 1, ["justifyContent"] : "space-between", ["alignItems"] : "center", ["flex"] : 1, ["display"] : "flex", ["padding"] : "10px", ["width"] : "100%", ["boxShadow"] : "0 var(--divider-px) 0 var(--gray-a6)", ["&[data-state='open'] > .AccordionChevron"] : ({ ["transform"] : "rotate(180deg)" }), ["&:hover"] : ({ ["backgroundColor"] : "#373a40" }), ["& > .AccordionChevron"] : ({ ["transition"] : "transform var(--animation-duration) var(--animation-easing)" }), ["&[data-variant='classic'], *:where([data-variant='classic']) &"] : ({ ["color"] : "var(--accent-contrast)", ["&:hover"] : ({ ["backgroundColor"] : "var(--accent-10)" }), ["& > .AccordionChevron"] : ({ ["color"] : "var(--accent-contrast)" }) }), ["background"] : "none", ["border"] : "none", ["backgroundColor"] : "#2c2e33", ["fontWeight"] : "bold", ["textAlign"] : "left" })},"Models")),jsx(RadixAccordionContent,{className:"AccordionContent",css:({ ["overflow"] : "visible", ["color"] : "var(--accent-11)", ["paddingInlineStart"] : "var(--space-4)", ["paddingInlineEnd"] : "var(--space-4)", ["&:before, &:after"] : ({ ["content"] : "' '", ["display"] : "block", ["height"] : "var(--space-3)" }), ["&[data-state='open']"] : ({ ["animation"] : (keyframes({ from: { height: 0 }, to: { height: "var(--radix-accordion-content-height)" } })+" var(--animation-duration) var(--animation-easing)") }), ["&[data-state='closed']"] : ({ ["animation"] : (keyframes({ from: { height: "var(--radix-accordion-content-height)" }, to: { height: 0 } })+" var(--animation-duration) var(--animation-easing)") }), ["&[data-variant='classic'], *:where([data-variant='classic']) &"] : ({ ["color"] : "var(--accent-contrast)" }), ["height"] : "auto" })},jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%" }),direction:"column",gap:"3"},jsx(Text_499af9570b2efb4ebad6d9423e9d15a9,{},),jsx(RadixThemesFlex,{align:"center",className:"rx-Stack",css:({ ["width"] : "100%", ["paddingTop"] : "1em", ["paddingBottom"] : "1em" }),direction:"row",gap:"3"},jsx(Select__root_ad027a400360796b695bb14958551772,{},),jsx(Button_cadca0cbd91512a210730cce4d71cfb2,{},))))),jsx(RadixAccordionItem,{className:"AccordionItem",css:({ ["overflow"] : "hidden", ["width"] : "100%", ["marginTop"] : "1px", ["borderTop"] : "var(--divider-px) solid var(--gray-a6)", ["&:first-child"] : ({ ["marginTop"] : 0, ["borderTop"] : 0, ["borderTopLeftRadius"] : "var(--radius-4)", ["borderTopRightRadius"] : "var(--radius-4)" }), ["&:last-child"] : ({ ["borderBottomLeftRadius"] : "var(--radius-4)", ["borderBottomRightRadius"] : "var(--radius-4)" }), ["&:focus-within"] : ({ ["position"] : "relative", ["zIndex"] : 1 }), ["&:first-child[data-variant='ghost'], *:where([data-variant='ghost']) &:first-child"] : ({ ["borderRadius"] : 0, ["borderTop"] : "var(--divider-px) solid var(--gray-a6)" }), ["&:last-child[data-variant='ghost'], *:where([data-variant='ghost']) &:last-child"] : ({ ["borderRadius"] : 0, ["borderBottom"] : "var(--divider-px) solid var(--gray-a6)" }), ["border"] : "1px solid #373a40", ["backgroundColor"] : "#25262b", ["marginBottom"] : "8px", ["borderRadius"] : "8px", ["paddingBottom"] : "2em" }),value:"mcp-tools"},jsx(RadixAccordionHeader,{className:"AccordionHeader",css:({ ["display"] : "flex", ["margin"] : "0" })},jsx(RadixAccordionTrigger,{className:"AccordionTrigger",css:({ ["color"] : "#e9ecef", ["fontSize"] : "1.1em", ["lineHeight"] : 1, ["justifyContent"] : "space-between", ["alignItems"] : "center", ["flex"] : 1, ["display"] : "flex", ["padding"] : "10px", ["width"] : "100%", ["boxShadow"] : "0 var(--divider-px) 0 var(--gray-a6)", ["&[data-state='open'] > .AccordionChevron"] : ({ ["transform"] : "rotate(180deg)" }), ["&:hover"] : ({ ["backgroundColor"] : "#373a40" }), ["& > .AccordionChevron"] : ({ ["transition"] : "transform var(--animation-duration) var(--animation-easing)" }), ["&[data-variant='classic'], *:where([data-variant='classic']) &"] : ({ ["color"] : "var(--accent-contrast)", ["&:hover"] : ({ ["backgroundColor"] : "var(--accent-10)" }), ["& > .AccordionChevron"] : ({ ["color"] : "var(--accent-contrast)" }) }), ["background"] : "none", ["border"] : "none", ["backgroundColor"] : "#2c2e33", ["fontWeight"] : "bold", ["textAlign"] : "left" })},"MCP Tools")),jsx(RadixAccordionContent,{className:"AccordionContent",css:({ ["overflow"] : "hidden", ["color"] : "var(--accent-11)", ["paddingInlineStart"] : "var(--space-4)", ["paddingInlineEnd"] : "var(--space-4)", ["&:before, &:after"] : ({ ["content"] : "' '", ["display"] : "block", ["height"] : "var(--space-3)" }), ["&[data-state='open']"] : ({ ["animation"] : (keyframes({ from: { height: 0 }, to: { height: "var(--radix-accordion-content-height)" } })+" var(--animation-duration) var(--animation-easing)") }), ["&[data-state='closed']"] : ({ ["animation"] : (keyframes({ from: { height: "var(--radix-accordion-content-height)" }, to: { height: 0 } })+" var(--animation-duration) var(--animation-easing)") }), ["&[data-variant='classic'], *:where([data-variant='classic']) &"] : ({ ["color"] : "var(--accent-contrast)" }) })},jsx(Flex_f5cf1ad59b80b4631a48389004c2814c,{},))),jsx(RadixAccordionItem,{className:"AccordionItem",css:({ ["overflow"] : "hidden", ["width"] : "100%", ["marginTop"] : "1px", ["borderTop"] : "var(--divider-px) solid var(--gray-a6)", ["&:first-child"] : ({ ["marginTop"] : 0, ["borderTop"] : 0, ["borderTopLeftRadius"] : "var(--radius-4)", ["borderTopRightRadius"] : "var(--radius-4)" }), ["&:last-child"] : ({ ["borderBottomLeftRadius"] : "var(--radius-4)", ["borderBottomRightRadius"] : "var(--radius-4)" }), ["&:focus-within"] : ({ ["position"] : "relative", ["zIndex"] : 1 }), ["&:first-child[data-variant='ghost'], *:where([data-variant='ghost']) &:first-child"] : ({ ["borderRadius"] : 0, ["borderTop"] : "var(--divider-px) solid var(--gray-a6)" }), ["&:last-child[data-variant='ghost'], *:where([data-variant='ghost']) &:last-child"] : ({ ["borderRadius"] : 0, ["borderBottom"] : "var(--divider-px) solid var(--gray-a6)" }), ["border"] : "1px solid #373a40", ["backgroundColor"] : "#25262b", ["marginBottom"] : "8px", ["borderRadius"] : "8px", ["paddingBottom"] : "2em" }),value:"built-in-mcps"},jsx(RadixAccordionHeader,{className:"AccordionHeader",css:({ ["display"] : "flex", ["margin"] : "0" })},jsx(RadixAccordionTrigger,{className:"AccordionTrigger",css:({ ["color"] : "#e9ecef", ["fontSize"] : "1.1em", ["lineHeight"] : 1, ["justifyContent"] : "space-between", ["alignItems"] : "center", ["flex"] : 1, ["display"] : "flex", ["padding"] : "10px", ["width"] : "100%", ["boxShadow"] : "0 var(--divider-px) 0 var(--gray-a6)", ["&[data-state='open'] > .AccordionChevron"] : ({ ["transform"] : "rotate(180deg)" }), ["&:hover"] : ({ ["backgroundColor"] : "#373a40" }), ["& > .AccordionChevron"] : ({ ["transition"] : "transform var(--animation-duration) var(--animation-easing)" }), ["&[data-variant='classic'], *:where([data-variant='classic']) &"] : ({ ["color"] : "var(--accent-contrast)", ["&:hover"] : ({ ["backgroundColor"] : "var(--accent-10)" }), ["& > .AccordionChevron"] : ({ ["color"] : "var(--accent-contrast)" }) }), ["background"] : "none", ["border"] : "none", ["backgroundColor"] : "#2c2e33", ["fontWeight"] : "bold", ["textAlign"] : "left" })},"Built-in MCPs")),jsx(RadixAccordionContent,{className:"AccordionContent",css:({ ["overflow"] : "hidden", ["color"] : "var(--accent-11)", ["paddingInlineStart"] : "var(--space-4)", ["paddingInlineEnd"] : "var(--space-4)", ["&:before, &:after"] : ({ ["content"] : "' '", ["display"] : "block", ["height"] : "var(--space-3)" }), ["&[data-state='open']"] : ({ ["animation"] : (keyframes({ from: { height: 0 }, to: { height: "var(--radix-accordion-content-height)" } })+" var(--animation-duration) var(--animation-easing)") }), ["&[data-state='closed']"] : ({ ["animation"] : (keyframes({ from: { height: "var(--radix-accordion-content-height)" }, to: { height: 0 } })+" var(--animation-duration) var(--animation-easing)") }), ["&[data-variant='classic'], *:where([data-variant='classic']) &"] : ({ ["color"] : "var(--accent-contrast)" }) })},jsx(Flex_c482eb1a15f8211eedc6c960b90b89bc,{},))),jsx(RadixAccordionItem,{className:"AccordionItem",css:({ ["overflow"] : "hidden", ["width"] : "100%", ["marginTop"] : "1px", ["borderTop"] : "var(--divider-px) solid var(--gray-a6)", ["&:first-child"] : ({ ["marginTop"] : 0, ["borderTop"] : 0, ["borderTopLeftRadius"] : "var(--radius-4)", ["borderTopRightRadius"] : "var(--radius-4)" }), ["&:last-child"] : ({ ["borderBottomLeftRadius"] : "var(--radius-4)", ["borderBottomRightRadius"] : "var(--radius-4)" }), ["&:focus-within"] : ({ ["position"] : "relative", ["zIndex"] : 1 }), ["&:first-child[data-variant='ghost'], *:where([data-variant='ghost']) &:first-child"] : ({ ["borderRadius"] : 0, ["borderTop"] : "var(--divider-px) solid var(--gray-a6)" }), ["&:last-child[data-variant='ghost'], *:where([data-variant='ghost']) &:last-child"] : ({ ["borderRadius"] : 0, ["borderBottom"] : "var(--divider-px) solid var(--gray-a6)" }), ["border"] : "1px solid #373a40", ["backgroundColor"] : "#25262b", ["marginBottom"] : "8px", ["borderRadius"] : "8px", ["paddingBottom"] : "2em" }),value:"autorun"},jsx(RadixAccordionHeader,{className:"AccordionHeader",css:({ ["display"] : "flex", ["margin"] : "0" })},jsx(RadixAccordionTrigger,{className:"AccordionTrigger",css:({ ["color"] : "#e9ecef", ["fontSize"] : "1.1em", ["lineHeight"] : 1, ["justifyContent"] : "space-between", ["alignItems"] : "center", ["flex"] : 1, ["display"] : "flex", ["padding"] : "10px", ["width"] : "100%", ["boxShadow"] : "0 var(--divider-px) 0 var(--gray-a6)", ["&[data-state='open'] > .AccordionChevron"] : ({ ["transform"] : "rotate(180deg)" }), ["&:hover"] : ({ ["backgroundColor"] : "#373a40" }), ["& > .AccordionChevron"] : ({ ["transition"] : "transform var(--animation-duration) var(--animation-easing)" }), ["&[data-variant='classic'], *:where([data-variant='classic']) &"] : ({ ["color"] : "var(--accent-contrast)", ["&:hover"] : ({ ["backgroundColor"] : "var(--accent-10)" }), ["& > .AccordionChevron"] : ({ ["color"] : "var(--accent-contrast)" }) }), ["background"] : "none", ["border"] : "none", ["backgroundColor"] : "#2c2e33", ["fontWeight"] : "bold", ["textAlign"] : "left" })},"Autorun")),jsx(RadixAccordionContent,{className:"AccordionContent",css:({ ["overflow"] : "hidden", ["color"] : "var(--accent-11)", ["paddingInlineStart"] : "var(--space-4)", ["paddingInlineEnd"] : "var(--space-4)", ["&:before, &:after"] : ({ ["content"] : "' '", ["display"] : "block", ["height"] : "var(--space-3)" }), ["&[data-state='open']"] : ({ ["animation"] : (keyframes({ from: { height: 0 }, to: { height: "var(--radix-accordion-content-height)" } })+" var(--animation-duration) var(--animation-easing)") }), ["&[data-state='closed']"] : ({ ["animation"] : (keyframes({ from: { height: "var(--radix-accordion-content-height)" }, to: { height: 0 } })+" var(--animation-duration) var(--animation-easing)") }), ["&[data-variant='classic'], *:where([data-variant='classic']) &"] : ({ ["color"] : "var(--accent-contrast)" }) })},jsx(RadixThemesText,{as:"p",css:({ ["color"] : "#adb5bd" })},"Run scripted prompts and capture screenshots."))),jsx(RadixAccordionItem,{className:"AccordionItem",css:({ ["overflow"] : "hidden", ["width"] : "100%", ["marginTop"] : "1px", ["borderTop"] : "var(--divider-px) solid var(--gray-a6)", ["&:first-child"] : ({ ["marginTop"] : 0, ["borderTop"] : 0, ["borderTopLeftRadius"] : "var(--radius-4)", ["borderTopRightRadius"] : "var(--radius-4)" }), ["&:last-child"] : ({ ["borderBottomLeftRadius"] : "var(--radius-4)", ["borderBottomRightRadius"] : "var(--radius-4)" }), ["&:focus-within"] : ({ ["position"] : "relative", ["zIndex"] : 1 }), ["&:first-child[data-variant='ghost'], *:where([data-variant='ghost']) &:first-child"] : ({ ["borderRadius"] : 0, ["borderTop"] : "var(--divider-px) solid var(--gray-a6)" }), ["&:last-child[data-variant='ghost'], *:where([data-variant='ghost']) &:last-child"] : ({ ["borderRadius"] : 0, ["borderBottom"] : "var(--divider-px) solid var(--gray-a6)" }), ["border"] : "1px solid #373a40", ["backgroundColor"] : "#25262b", ["marginBottom"] : "8px", ["borderRadius"] : "8px", ["paddingBottom"] : "2em" }),value:"logging"},jsx(RadixAccordionHeader,{className:"AccordionHeader",css:({ ["display"] : "flex", ["margin"] : "0" })},jsx(RadixAccordionTrigger,{className:"AccordionTrigger",css:({ ["color"] : "#e9ecef", ["fontSize"] : "1.1em", ["lineHeight"] : 1, ["justifyContent"] : "space-between", ["alignItems"] : "center", ["flex"] : 1, ["display"] : "flex", ["padding"] : "10px", ["width"] : "100%", ["boxShadow"] : "0 var(--divider-px) 0 var(--gray-a6)", ["&[data-state='open'] > .AccordionChevron"] : ({ ["transform"] : "rotate(180deg)" }), ["&:hover"] : ({ ["backgroundColor"] : "#373a40" }), ["& > .AccordionChevron"] : ({ ["transition"] : "transform var(--animation-duration) var(--animation-easing)" }), ["&[data-variant='classic'], *:where([data-variant='classic']) &"] : ({ ["color"] : "var(--accent-contrast)", ["&:hover"] : ({ ["backgroundColor"] : "var(--accent-10)" }), ["& > .AccordionChevron"] : ({ ["color"] : "var(--accent-contrast)" }) }), ["background"] : "none", ["border"] : "none", ["backgroundColor"] : "#2c2e33", ["fontWeight"] : "bold", ["textAlign"] : "left" })},"Logging")),jsx(RadixAccordionContent,{className:"AccordionContent",css:({ ["overflow"] : "hidden", ["color"] : "var(--accent-11)", ["paddingInlineStart"] : "var(--space-4)", ["paddingInlineEnd"] : "var(--space-4)", ["&:before, &:after"] : ({ ["content"] : "' '", ["display"] : "block", ["height"] : "var(--space-3)" }), ["&[data-state='open']"] : ({ ["animation"] : (keyframes({ from: { height: 0 }, to: { height: "var(--radix-accordion-content-height)" } })+" var(--animation-duration) var(--animation-easing)") }), ["&[data-state='closed']"] : ({ ["animation"] : (keyframes({ from: { height: "var(--radix-accordion-content-height)" }, to: { height: 0 } })+" var(--animation-duration) var(--animation-easing)") }), ["&[data-variant='classic'], *:where([data-variant='classic']) &"] : ({ ["color"] : "var(--accent-contrast)" }) })},jsx(RadixThemesText,{as:"p",css:({ ["color"] : "#adb5bd" })},"Session logs, interaction JSON, and diagnostics."))),jsx(RadixAccordionItem,{className:"AccordionItem",css:({ ["overflow"] : "hidden", ["width"] : "100%", ["marginTop"] : "1px", ["borderTop"] : "var(--divider-px) solid var(--gray-a6)", ["&:first-child"] : ({ ["marginTop"] : 0, ["borderTop"] : 0, ["borderTopLeftRadius"] : "var(--radius-4)", ["borderTopRightRadius"] : "var(--radius-4)" }), ["&:last-child"] : ({ ["borderBottomLeftRadius"] : "var(--radius-4)", ["borderBottomRightRadius"] : "var(--radius-4)" }), ["&:focus-within"] : ({ ["position"] : "relative", ["zIndex"] : 1 }), ["&:first-child[data-variant='ghost'], *:where([data-variant='ghost']) &:first-child"] : ({ ["borderRadius"] : 0, ["borderTop"] : "var(--divider-px) solid var(--gray-a6)" }), ["&:last-child[data-variant='ghost'], *:where([data-variant='ghost']) &:last-child"] : ({ ["borderRadius"] : 0, ["borderBottom"] : "var(--divider-px) solid var(--gray-a6)" }), ["border"] : "1px solid #373a40", ["backgroundColor"] : "#25262b", ["marginBottom"] : "8px", ["borderRadius"] : "8px", ["paddingBottom"] : "2em" }),value:"diagnostics"},jsx(RadixAccordionHeader,{className:"AccordionHeader",css:({ ["display"] : "flex", ["margin"] : "0" })},jsx(Trigger_66247fc47dcba02740b522ecd3bfd144,{},)),jsx(RadixAccordionContent,{className:"AccordionContent",css:({ ["overflow"] : "hidden", ["color"] : "var(--accent-11)", ["paddingInlineStart"] : "var(--space-4)", ["paddingInlineEnd"] : "var(--space-4)", ["&:before, &:after"] : ({ ["content"] : "' '", ["display"] : "block", ["height"] : "var(--space-3)" }), ["&[data-state='open']"] : ({ ["animation"] : (keyframes({ from: { height: 0 }, to: { height: "var(--radix-accordion-content-height)" } })+" var(--animation-duration) var(--animation-easing)") }), ["&[data-state='closed']"] : ({ ["animation"] : (keyframes({ from: { height: "var(--radix-accordion-content-height)" }, to: { height: 0 } })+" var(--animation-duration) var(--animation-easing)") }), ["&[data-variant='classic'], *:where([data-variant='classic']) &"] : ({ ["color"] : "var(--accent-contrast)" }) })},jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%" }),direction:"column",gap:"2"},jsx(Text_242f86d24710c0f8ec0f610c5d56ee95,{},),jsx(Text_9205caafe22c707e74f27adda3dfc04e,{},),jsx(Text_c1707882608b8d057d06458a64b4e33c,{},),jsx(Text_63e7450d9174018faf1af5865840d6eb,{},),jsx(Text_0ae37c0d7e84d43257464e2c2a3ac115,{},)))))))))):(jsx(Fragment,{},))))
  )
}


function Panel_977ad23e93d0a0864d3b7abd79a3e3b0 () {
  const ref_settings = useRef(null); refs["ref_settings"] = ref_settings;
const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(ResizablePanel,{css:({ ["display"] : (reflex___state____state__pepper_reflex___state____base_state.show_settings_rx_state_ ? "flex" : "none") }),defaultSize:(reflex___state____state__pepper_reflex___state____base_state.show_settings_rx_state_ ? ((reflex___state____state__pepper_reflex___state____base_state.show_chat_rx_state_ && reflex___state____state__pepper_reflex___state____base_state.show_cards_rx_state_) ? 33 : ((reflex___state____state__pepper_reflex___state____base_state.show_chat_rx_state_ || reflex___state____state__pepper_reflex___state____base_state.show_cards_rx_state_) ? 50 : 100)) : 0),id:"settings",maxSize:(reflex___state____state__pepper_reflex___state____base_state.show_settings_rx_state_ ? 100 : 0),minSize:(reflex___state____state__pepper_reflex___state____base_state.show_settings_rx_state_ ? 15 : 0),order:1,ref:ref_settings},jsx(Fragment_e910531d68efb7757da93546d7f2461a,{},))
  )
}


function Fragment_efe5a35af2c58ad90ba945d34f8249c8 () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(Fragment,{},((reflex___state____state__pepper_reflex___state____base_state.show_settings_rx_state_ && (reflex___state____state__pepper_reflex___state____base_state.show_chat_rx_state_ || reflex___state____state__pepper_reflex___state____base_state.show_cards_rx_state_))?(jsx(Fragment,{},jsx(ResizablePanelResizeHandle,{css:({ ["width"] : "4px", ["background"] : "var(--accent-9)", ["backgroundColor"] : "#373a40" })},))):(jsx(Fragment,{},))))
  )
}


function Debounceinput_584d79b8e03b15c4b5d26243b1504223 () {
  const reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____chat_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____chat_state)
const [addEvents, connectErrors] = useContext(EventLoopContext);

const on_change_a118291d36e77b662118a92baff72444 = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.pepper_reflex___state____base_state.pepper_reflex___state____chat_state.set_input_text", ({ ["value"] : _e?.["target"]?.["value"] }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])

  return (
    jsx(DebounceInput,{css:({ ["color"] : "white", ["backgroundColor"] : "#25262b", ["width"] : "90%", ["height"] : "70px", ["placeholderColor"] : "#909296", ["border"] : "1px solid #373a40", ["focusBorderColor"] : "#4dabf7", ["fontFamily"] : "Inter, 'Segoe UI', sans-serif", ["--default-font-family"] : "Inter, 'Segoe UI', sans-serif", ["padding"] : "10px" }),debounceTimeout:300,element:RadixThemesTextArea,onChange:on_change_a118291d36e77b662118a92baff72444,placeholder:"Type a message...",value:reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____chat_state.input_text_rx_state_},)
  )
}


function Button_75d360593f234eec5aff83ac44d64645 () {
  const [addEvents, connectErrors] = useContext(EventLoopContext);

const on_click_a371540a496e811de207abbd11ea8b96 = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.pepper_reflex___state____base_state.pepper_reflex___state____chat_state.send_message", ({  }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])

  return (
    jsx(RadixThemesButton,{css:({ ["width"] : "10%", ["height"] : "70px", ["backgroundColor"] : "#4dabf7", ["color"] : "#1a1b1e", ["fontWeight"] : "bold", ["borderRadius"] : "2px" }),onClick:on_click_a371540a496e811de207abbd11ea8b96,size:"2"},"Send")
  )
}


function Flex_491c326234af0f635f6eb394a91ef9dc () {
  const reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____chat_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____chat_state)



  return (
    jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%", ["height"] : "100%", ["padding"] : "8px", ["alignItems"] : "stretch" }),direction:"column",gap:"2"},Array.prototype.map.call(reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____chat_state.messages_rx_state_ ?? [],((msg_rx_state_,index_3097fd87524e09af5c0b7629eec2cdbe)=>(jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%" }),direction:"row",justify:((msg_rx_state_?.["role"]?.valueOf?.() === "user"?.valueOf?.()) ? "flex-end" : "flex-start"),key:index_3097fd87524e09af5c0b7629eec2cdbe,gap:"3"},jsx(RadixThemesBox,{css:({ ["padding"] : "8px 10px", ["backgroundColor"] : ((msg_rx_state_?.["role"]?.valueOf?.() === "mcp_request"?.valueOf?.()) ? "#1f2329" : ((msg_rx_state_?.["role"]?.valueOf?.() === "user"?.valueOf?.()) ? "#373a40" : "#2b3a4d")), ["border"] : ((msg_rx_state_?.["role"]?.valueOf?.() === "mcp_request"?.valueOf?.()) ? "1px solid #000000" : "1px solid #373a40"), ["borderRadius"] : ((msg_rx_state_?.["role"]?.valueOf?.() === "mcp_request"?.valueOf?.()) ? "4px" : "10px"), ["maxWidth"] : "80%" })},jsx(RadixThemesText,{as:"p",css:({ ["fontSize"] : "0.9rem", ["fontFamily"] : ((msg_rx_state_?.["role"]?.valueOf?.() === "mcp_request"?.valueOf?.()) ? "'JetBrains Mono', 'Fira Code', monospace" : "Inter, 'Segoe UI', sans-serif"), ["--default-font-family"] : ((msg_rx_state_?.["role"]?.valueOf?.() === "mcp_request"?.valueOf?.()) ? "'JetBrains Mono', 'Fira Code', monospace" : "Inter, 'Segoe UI', sans-serif"), ["color"] : "#e9ecef" })},msg_rx_state_?.["text"])))))),jsx(RadixThemesFlex,{align:"center",className:"rx-Stack",css:({ ["padding"] : "8px", ["backgroundColor"] : "#25262b", ["borderTop"] : "1px solid #373a40", ["width"] : "100%", ["marginTop"] : "auto" }),direction:"row",gap:"2"},jsx(Debounceinput_584d79b8e03b15c4b5d26243b1504223,{},),jsx(Button_75d360593f234eec5aff83ac44d64645,{},)))
  )
}


function Fragment_dbdd3f1e7b9c0bc31b762d3e61f295db () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(Fragment,{},(reflex___state____state__pepper_reflex___state____base_state.show_chat_rx_state_?(jsx(Fragment,{},jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["height"] : "100%", ["flex"] : "1" }),direction:"column",gap:"0"},jsx(RadixThemesBox,{css:({ ["padding"] : "6px 10px", ["backgroundColor"] : "#2c2e33", ["borderBottom"] : "1px solid #373a40", ["color"] : "#e9ecef", ["fontWeight"] : "bold", ["fontFamily"] : "Inter, 'Segoe UI', sans-serif", ["--default-font-family"] : "Inter, 'Segoe UI', sans-serif", ["width"] : "100%" })},jsx(RadixThemesText,{as:"p",css:({ ["fontWeight"] : "bold", ["color"] : "#e9ecef" })},"Chat")),jsx(RadixThemesBox,{css:({ ["overflowY"] : "auto", ["flex"] : "1", ["width"] : "100%", ["overflow"] : "hidden" })},jsx(Flex_491c326234af0f635f6eb394a91ef9dc,{},))))):(jsx(Fragment,{},))))
  )
}


function Panel_1bdd188c55bb5d4c2504b1e4ad17cd3b () {
  const ref_chat = useRef(null); refs["ref_chat"] = ref_chat;
const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(ResizablePanel,{css:({ ["display"] : (reflex___state____state__pepper_reflex___state____base_state.show_chat_rx_state_ ? "flex" : "none") }),defaultSize:(reflex___state____state__pepper_reflex___state____base_state.show_chat_rx_state_ ? (reflex___state____state__pepper_reflex___state____base_state.show_cards_rx_state_ ? 50 : 100) : 0),id:"chat",maxSize:(reflex___state____state__pepper_reflex___state____base_state.show_chat_rx_state_ ? 100 : 0),minSize:(reflex___state____state__pepper_reflex___state____base_state.show_chat_rx_state_ ? 20 : 0),order:1,ref:ref_chat},jsx(Fragment_dbdd3f1e7b9c0bc31b762d3e61f295db,{},))
  )
}


function Fragment_f2de9b8eb02230ff25ba0bbfebd7a80c () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(Fragment,{},((reflex___state____state__pepper_reflex___state____base_state.show_chat_rx_state_ && reflex___state____state__pepper_reflex___state____base_state.show_cards_rx_state_)?(jsx(Fragment,{},jsx(ResizablePanelResizeHandle,{css:({ ["width"] : "4px", ["background"] : "var(--accent-9)", ["backgroundColor"] : "#373a40" })},))):(jsx(Fragment,{},))))
  )
}


function Flex_f7805e939f08e474578c2dc9cff3b765 () {
  const reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____cards_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____cards_state)



  return (
    jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["padding"] : "12px", ["width"] : "100%" }),direction:"column",gap:"4"},Array.prototype.map.call(reflex___state____state__pepper_reflex___state____base_state__pepper_reflex___state____cards_state.cards_rx_state_ ?? [],((title_rx_state_,index_c13981f6adb6a0b67a367adf09323a99)=>(jsx(RadixThemesCard,{css:({ ["width"] : "100%", ["height"] : "240px", ["padding"] : "20px", ["backgroundColor"] : "#ffffff", ["border"] : "1px solid #999", ["borderRadius"] : "8px" }),key:index_c13981f6adb6a0b67a367adf09323a99},jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["height"] : "100%" }),direction:"column",gap:"2"},jsx(RadixThemesText,{as:"p",css:({ ["fontWeight"] : "bold", ["color"] : "#111111" })},title_rx_state_),jsx(RadixThemesText,{as:"p",css:({ ["fontSize"] : "0.9rem", ["color"] : "#111111" })},"SVG card placeholder")))))))
  )
}


function Fragment_344c19b84a551e19935c66a1cff05fd5 () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(Fragment,{},(reflex___state____state__pepper_reflex___state____base_state.show_cards_rx_state_?(jsx(Fragment,{},jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["height"] : "100%", ["flex"] : "1", ["backgroundColor"] : "#1a1b1e" }),direction:"column",gap:"0"},jsx(RadixThemesBox,{css:({ ["padding"] : "6px 10px", ["backgroundColor"] : "#2c2e33", ["borderBottom"] : "1px solid #373a40", ["color"] : "#e9ecef", ["fontWeight"] : "bold", ["fontFamily"] : "Inter, 'Segoe UI', sans-serif", ["--default-font-family"] : "Inter, 'Segoe UI', sans-serif", ["width"] : "100%" })},jsx(RadixThemesText,{as:"p",css:({ ["fontWeight"] : "bold" })},"Cards")),jsx(RadixThemesBox,{css:({ ["overflowY"] : "auto", ["flex"] : "1", ["width"] : "100%" })},jsx(Flex_f7805e939f08e474578c2dc9cff3b765,{},))))):(jsx(Fragment,{},))))
  )
}


function Panel_c7d58e4abf68bd7d77c21cedd407d428 () {
  const ref_cards = useRef(null); refs["ref_cards"] = ref_cards;
const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(ResizablePanel,{css:({ ["display"] : (reflex___state____state__pepper_reflex___state____base_state.show_cards_rx_state_ ? "flex" : "none") }),defaultSize:(reflex___state____state__pepper_reflex___state____base_state.show_cards_rx_state_ ? (reflex___state____state__pepper_reflex___state____base_state.show_chat_rx_state_ ? 50 : 100) : 0),id:"cards",maxSize:(reflex___state____state__pepper_reflex___state____base_state.show_cards_rx_state_ ? 100 : 0),minSize:(reflex___state____state__pepper_reflex___state____base_state.show_cards_rx_state_ ? 15 : 0),order:2,ref:ref_cards},jsx(Fragment_344c19b84a551e19935c66a1cff05fd5,{},))
  )
}


function Panelgroup_f5eb59a0e64de1cc61bbc6f790a90beb () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)



  return (
    jsx(ResizablePanelGroup,{direction:"horizontal",key:(reflex___state____state__pepper_reflex___state____base_state.show_chat_rx_state_ ? (reflex___state____state__pepper_reflex___state____base_state.show_cards_rx_state_ ? "layout-inner-11" : "layout-inner-10") : (reflex___state____state__pepper_reflex___state____base_state.show_cards_rx_state_ ? "layout-inner-01" : "layout-inner-00"))},jsx(Panel_1bdd188c55bb5d4c2504b1e4ad17cd3b,{},),jsx(Fragment_f2de9b8eb02230ff25ba0bbfebd7a80c,{},),jsx(Panel_c7d58e4abf68bd7d77c21cedd407d428,{},))
  )
}


function Panelgroup_91523848a7e43405fbe583d1a419ab08 () {
  const reflex___state____state__pepper_reflex___state____base_state = useContext(StateContexts.reflex___state____state__pepper_reflex___state____base_state)
const ref_main_content = useRef(null); refs["ref_main_content"] = ref_main_content;



  return (
    jsx(ResizablePanelGroup,{css:({ ["height"] : "100%" }),direction:"horizontal",key:(reflex___state____state__pepper_reflex___state____base_state.show_settings_rx_state_ ? (reflex___state____state__pepper_reflex___state____base_state.show_chat_rx_state_ ? (reflex___state____state__pepper_reflex___state____base_state.show_cards_rx_state_ ? "layout-111" : "layout-110") : "layout-100") : (reflex___state____state__pepper_reflex___state____base_state.show_chat_rx_state_ ? (reflex___state____state__pepper_reflex___state____base_state.show_cards_rx_state_ ? "layout-011" : "layout-010") : "layout-001"))},jsx(Panel_977ad23e93d0a0864d3b7abd79a3e3b0,{},),jsx(Fragment_efe5a35af2c58ad90ba945d34f8249c8,{},),jsx(ResizablePanel,{id:"main-content",order:2,ref:ref_main_content},jsx(Panelgroup_f5eb59a0e64de1cc61bbc6f790a90beb,{},)))
  )
}


export default function Component() {





  return (
    jsx(Fragment,{},jsx(RadixThemesTheme,{css:{...theme.styles.global[':root'], ...theme.styles.global.body}},jsx(RadixThemesFlex,{css:({ ["height"] : "100vh", ["maxHeight"] : "100vh", ["overflow"] : "hidden", ["width"] : "100%", ["backgroundColor"] : "#1a1b1e" }),direction:"column"},jsx("style",{suppressHydrationWarning:true},"\n                .rt-TextAreaInput, .rt-TextAreaRoot textarea, textarea {\n                    color: #ffffff !important;\n                    -webkit-text-fill-color: #ffffff !important;\n                    background-color: #25262b !important;\n                }\n                .rt-TextAreaInput:focus, textarea:focus {\n                    outline: 1px solid #4dabf7 !important;\n                }\n                textarea::placeholder {\n                    color: #adb5bd !important;\n                }\n                "),jsx(Fragment_c0a0b3abf1673d25f69e0fd63bb8027a,{},),jsx(RadixThemesFlex,{align:"center",className:"rx-Stack",css:({ ["padding"] : "6px 10px", ["borderBottom"] : "1px solid #373a40", ["backgroundColor"] : "#2c2e33", ["color"] : "#e9ecef", ["width"] : "100%" }),direction:"row",gap:"3"},jsx(RadixThemesText,{as:"p",css:({ ["fontWeight"] : "bold", ["color"] : "#e9ecef" })},jsx(Fragment_498f8c69dd34716005332c2269185b1d,{},)),jsx(RadixThemesFlex,{css:({ ["flex"] : 1, ["justifySelf"] : "stretch", ["alignSelf"] : "stretch" })},),jsx(RadixThemesFlex,{align:"center",className:"rx-Stack",direction:"row",gap:"2"},jsx(Text_dfbdefd3c75647074d62ea5c75d930da,{},),jsx(Progress_0c62b0acefcf110a865e6b4de6f811de,{},),jsx(Button_a5b424af077f0e7d8fbbe467a9827eb8,{},),jsx(Button_51f532c4831f34e9349288686fba0557,{},),jsx(Button_876b0f2b9bc2c7944ef8069078c5f53f,{},))),jsx(Panelgroup_91523848a7e43405fbe583d1a419ab08,{},))),jsx("title",{},"PepperReflex | Index"),jsx("meta",{content:"favicon.ico",property:"og:image"},))
  )
}