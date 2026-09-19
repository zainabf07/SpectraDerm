import type { ReactNode } from "react";
export function Loading({children="Preparing your observation…"}:{children?:ReactNode}) { return <p className="state loading" role="status">{children}</p>; }
export function Empty({children}:{children:ReactNode}) { return <section className="state empty">{children}</section>; }
export function ErrorState({message, retry}:{message?:string;retry?:()=>void}) { return <section className="state error" role="alert"><p>{message || "Something went wrong while analyzing this scan."}</p>{retry && <button className="button secondary" onClick={retry}>Try again</button>}</section>; }
