import { useState } from "react";
import { ArrowRight, BookOpen, MagnifyingGlass } from "@phosphor-icons/react";
import { authoredDemos } from "../components/Phase12Demo";
import { DEFAULT_CODE, examples } from "../constants/examples";
import { Engraving, type Destination } from "./Shell";
import type { ExampleCase } from "./Intention";

type Lesson = { name:string; description:string; topic:string; level:"Beginner"|"Intermediate"|"Advanced";
  source:string; route:"compiler"|"intention"; entry?:string; tests?:ExampleCase[] };
const demos = authoredDemos;
const checks = (rows: (number | boolean)[][]): ExampleCase[] => rows.map(row => ({args:row.slice(0,-1),expected_return:row[row.length-1]}));

export const lessons: Lesson[] = [
  {name:"A correct program", description:"Compile a program and follow its conditional return.", topic:"Compiler", level:"Beginner", source:DEFAULT_CODE,route:"compiler"},
  {name:"Missing semicolon", description:"Locate a syntax diagnostic and review the compiler fix.", topic:"Compiler",level:"Beginner",source:examples["Missing Semicolon"],route:"compiler"},
  {name:"Addition or subtraction?", description:"Use expected sums to constrain a one-operator repair.", topic:"Arithmetic",level:"Beginner",
    source:"int add(int a, int b) {\n    return a - b;\n}",route:"intention",entry:"add",tests:checks([[5,3,8],[10,2,12],[4,7,11]])},
  {name:"An exclusive loop bound",description:"Check what happens at the first index outside an array.",topic:"Arrays & loops",level:"Intermediate",
    source:"int total(int x, int y, int z) {\n    int a[3]; a[0] = x; a[1] = y; a[2] = z;\n    int sum = 0;\n    for (int i = 0; i <= 3; i++) { sum += a[i]; }\n    return sum;\n}",route:"intention",entry:"total",tests:checks([[5,3,8,16],[10,2,12,24],[4,7,-2,9]])},
  {name:"An index needs a contract",description:"Inspect why a physical extent alone cannot establish an intended index.",topic:"Arrays & loops",level:"Intermediate",
    source:demos[4].source,route:"intention",entry:"demo"},
  {name:"A function with two branches",description:"Inspect scoped declarations and the function return paths.",topic:"Functions",level:"Beginner",
    source:"int maximum(int a, int b) {\n    if (a > b) { return a; }\n    return b;\n}",route:"compiler"},
  {name:"Recursive factorial",description:"Trace the base case and the call that reduces the input.",topic:"Functions",level:"Intermediate",
    source:"int factorial(int n) {\n    if (n <= 1) { return 1; }\n    return n * factorial(n - 1);\n}",route:"intention",entry:"factorial",tests:checks([[0,1],[3,6],[5,120]])},
  {name:demos[3].label,description:"Compare distinct changes that fit the same interpolation observations.",topic:"Repair evidence",level:"Advanced",
    source:demos[3].source,route:"intention",entry:"f",tests:demos[3].examples},
  {name:"An empty logical prefix",description:"Give a fixed array scan an explicit result for length zero.",topic:"Arrays & loops",level:"Advanced",
    source:"int total(int n, int x, int y) {\n    int a[2]; a[0] = x; a[1] = y;\n    int sum = a[0];\n    for (int i = 1; i < n; i++) { sum += a[i]; }\n    return sum;\n}",route:"intention",entry:"total",tests:checks([[0,9,4,-8],[1,2,8,2],[2,3,4,7]])},
  {name:"Sentinel collision",description:"Keep −1 as a legitimate value by checking presence explicitly.",topic:"Repair evidence",level:"Intermediate",
    source:demos[2].source,route:"intention",entry:"demo",tests:demos[2].examples},
];

export function ExamplesWorkspace({load}: {load:(example:Lesson)=>void}) {
  const [search,setSearch] = useState("");
  const [topic,setTopic] = useState("");
  const [level,setLevel] = useState("");
  const topics = [...new Set(lessons.map(item => item.topic))];
  const results = lessons.filter(item => (!topic || item.topic === topic) && (!level || item.level === level)
    && `${item.name} ${item.description} ${item.topic}`.toLowerCase().includes(search.trim().toLowerCase()));
  const art = (lesson: Lesson): Destination => lesson.topic === "Compiler" ? "compiler" : lesson.topic === "Repair evidence" ? "intention"
    : lesson.topic === "Arrays & loops" ? "research" : "examples";
  return <>
    <section className="paper-card example-filters" aria-label="Filter examples">
      <label><span><MagnifyingGlass size={17} /> Search examples</span><input type="search" value={search} onChange={event => setSearch(event.target.value)}
        placeholder="Search by concept or title" /></label>
      <label>Topic<select aria-label="Topic" value={topic} onChange={e => setTopic(e.target.value)}><option value="">All topics</option>
        {topics.map(item => <option key={item}>{item}</option>)}</select></label>
      <label>Difficulty<select aria-label="Difficulty" value={level} onChange={e => setLevel(e.target.value)}><option value="">All levels</option>
        {["Beginner","Intermediate","Advanced"].map(item => <option key={item}>{item}</option>)}</select></label>
    </section>
    <div className="learning-layout">
      <section aria-label="Example library">{!results.length && <p role="status">No examples match these filters.</p>}
        <div className="lesson-cards">{results.map(item => <article className="paper-card lesson-card" key={item.name}>
          <div className="lesson-art"><Engraving topic={art(item)} /></div>
          <div className="lesson-meta"><span>{item.topic}</span><span className="p14-badge">{item.level}</span></div>
          <h2>{item.name}</h2><p>{item.description}</p>
          <pre><code>{item.source.split("\n").slice(0,4).join("\n")}</code></pre>
          <button type="button" onClick={() => load(item)} aria-label={`Try Example: ${item.name}`}>Try Example <ArrowRight size={17} /></button>
        </article>)}</div>
      </section>
      <aside className="paper-card guided-learning"><h2><BookOpen /> Guided Learning</h2>
        <ol>{[["Understand the program",0],["Analyze compiler errors",1],["Detect behavioral mismatches",2],
          ["Review suggested repairs",9],["Inspect technical evidence",7]].map(([label,index]) =>
          <li key={label}><button type="button" onClick={() => load(lessons[Number(index)])}>{label}</button></li>)}</ol>
        <p>Each exercise loads its source and any supplied expectations.</p>
      </aside>
    </div>
  </>;
}
