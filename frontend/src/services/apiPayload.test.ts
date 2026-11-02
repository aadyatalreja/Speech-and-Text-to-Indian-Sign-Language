import { afterEach, expect, it, vi } from "vitest";
const { post } = vi.hoisted(() => ({ post: vi.fn(async () => ({ data: {} })) }));
vi.mock("axios", () => ({ default: { create: () => ({post}), isAxiosError: () => false } }));
import { reportSign, streamTranslate, translate } from "./api";

afterEach(() => { post.mockClear(); vi.unstubAllGlobals(); });
it("sends selected input language for standard and live requests", async () => {
  await translate("नमस्ते","hi-IN");
  expect(post).toHaveBeenCalledWith("/translate",{text:"नमस्ते",source_language:"hi-IN",target_sign_language:"ISL"});
  class Socket {
    static last: Socket;
    onopen?:()=>void; onmessage?:()=>void; onerror?:()=>void;
    send=vi.fn((_data: string) => {}); close=vi.fn();
    constructor(_url:string) { Socket.last=this; }
  }
  vi.stubGlobal("WebSocket",Socket); vi.stubGlobal("location",{protocol:"http:",host:"localhost"});
  const close=streamTranslate("ನಮಸ್ಕಾರ",vi.fn(),"kn-IN");
  Socket.last.onopen!();
  expect(JSON.parse(Socket.last.send.mock.calls[0][0])).toEqual({text:"ನಮಸ್ಕಾರ",source_language:"kn-IN"});
  close(); expect(Socket.last.close).toHaveBeenCalledOnce();
});
it("sends explicit report fields without account or peer identifiers",async()=>{
  const report={gloss:"HELLO",sign_id:"hello",sentence:"Hello",note:"test",timestamp:"2026-11-02T00:00:00Z"};
  await reportSign(report);
  expect(post).toHaveBeenCalledWith("/feedback",report);
});
