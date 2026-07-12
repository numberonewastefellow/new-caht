# PythonTool Chart Rendering — Architecture & Implementation Guide

## Overview

The PythonTool (Code Interpreter) executes Python code in a Docker sandbox. When agents generate matplotlib charts via `plt.savefig()`, the resulting PNG files are:

1. Downloaded from the sandbox
2. Saved to the VertualAI FileStore (S3/Postgres)
3. Streamed to the frontend as `file_ids` in `PythonToolDelta` packets
4. **Rendered inline** in the chat UI using the `InMessageImage` component
5. **Persisted** in chat history via `create_python_tool_packets()` in `session_loading.py`

## Architecture

```
Code (plt.savefig('chart.png'))
  -> Docker sandbox generates PNG
  -> python_tool.py downloads from sandbox
  -> Saves to FileStore (onyx_file_id = file_store.save_file(...))
  -> Emits PythonToolDelta(file_ids=[...], files=[{file_id, filename}])
  -> Frontend PythonToolRenderer.tsx renders InMessageImage for image files
  -> On history reload, session_loading.py reconstructs packets from ToolCall DB record
```

### Key Files

| File | Role |
|------|------|
| `backend/onyx/server/query_and_chat/streaming_models.py` | `PythonToolFile` model, `PythonToolDelta.files` field |
| `backend/onyx/tools/tool_implementations/python/python_tool.py` | Emits enriched `files` list in delta packets |
| `backend/onyx/server/query_and_chat/session_loading.py` | `create_python_tool_packets()` for history reconstruction |
| `web/src/app/app/services/streamingModels.ts` | TypeScript `PythonToolFile` interface |
| `web/src/app/app/message/messageComponents/timeline/renderers/code/PythonToolRenderer.tsx` | Renders chart images inline |
| `web/src/app/app/components/files/images/InMessageImage.tsx` | Reusable image component (lazy load, modal, download) |
| `web/src/app/app/components/files/images/utils.ts` | `buildImgUrl(fileId)` -> `/api/chat/file/{fileId}` |

### Data Flow

**Live streaming:**
```
PythonToolStart { code } -> PythonToolDelta { stdout, stderr, file_ids, files } -> SectionEnd
```

**History reload:**
```
ToolCall DB record -> tool_call_arguments["code"] + tool_call_response (JSON with generated_files)
  -> create_python_tool_packets() reconstructs Start + Delta + SectionEnd
```

### File Type Detection

The frontend distinguishes image files from other generated files by extension:
- **Image extensions**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp`
- Images are rendered inline using `InMessageImage` (with modal fullscreen + download)
- Non-image files show a download link

---

## Future Upgrade: Interactive Charts with Plotly / React Charts

### Option A: Plotly (Recommended)

Plotly generates interactive JSON chart specs that can be rendered client-side.

#### Backend Changes

1. **Agent prompts**: Update coding agent prompts to prefer Plotly over matplotlib:
   ```python
   # Instead of:
   plt.savefig('chart.png')
   # Generate:
   import plotly.express as px
   fig = px.bar(df, x='category', y='value')
   fig.write_json('chart.plotly.json')
   ```

2. **Docker sandbox**: Ensure `plotly` is installed in the Code Interpreter Docker image.

3. **File detection**: The `.plotly.json` extension signals an interactive chart (vs static `.png`).

4. **No changes needed** to `PythonToolDelta` — files are already streamed with filenames.

#### Frontend Changes

1. **Install dependency**:
   ```bash
   npm install react-plotly.js plotly.js
   ```

2. **Create `PlotlyChartRenderer.tsx`**:
   ```tsx
   import Plot from 'react-plotly.js';

   interface PlotlyChartProps {
     fileId: string;
   }

   export function PlotlyChart({ fileId }: PlotlyChartProps) {
     const [spec, setSpec] = useState<any>(null);

     useEffect(() => {
       fetch(buildImgUrl(fileId))
         .then(res => res.json())
         .then(setSpec);
     }, [fileId]);

     if (!spec) return <Skeleton />;
     return <Plot data={spec.data} layout={spec.layout} />;
   }
   ```

3. **Update `PythonToolRenderer.tsx`**:
   - Detect `.plotly.json` files by extension
   - Render with `PlotlyChart` instead of `InMessageImage`
   - All other files (PNG, CSV, etc.) continue rendering as before

#### Considerations
- **Bundle size**: `plotly.js` is ~3MB. Use dynamic `import()` for code splitting.
- **SSR**: Plotly requires browser APIs. Use `dynamic(() => import(...), { ssr: false })`.
- **Fallback**: If Plotly rendering fails, show a "Download chart data" link.

### Option B: Recharts (Lighter Alternative)

Recharts is a React-native charting library with smaller bundle size (~200KB).

#### Approach
- Agent generates a JSON data spec with chart type + data
- Frontend maps chart type to Recharts components (`BarChart`, `LineChart`, etc.)

#### Tradeoffs vs Plotly
| Aspect | Plotly | Recharts |
|--------|--------|----------|
| Bundle size | ~3MB (heavy) | ~200KB (light) |
| Chart variety | 50+ chart types | ~15 chart types |
| Interactivity | Built-in zoom, pan, hover | Manual implementation |
| Agent complexity | Simple (`fig.write_json()`) | Requires structured JSON spec |
| 3D charts | Yes | No |

#### Recommendation
Start with **Plotly** for maximum flexibility and agent simplicity. The agent just calls `fig.write_json()` and the frontend renders it. If bundle size becomes a concern, lazy-load Plotly only when `.plotly.json` files are present.

### Option C: Hybrid (Best of Both)

1. Use **Plotly** for complex/interactive charts (`.plotly.json`)
2. Keep **PNG** for simple static charts (`.png`)
3. Let the agent decide based on complexity

This is the recommended long-term approach.

---

## Testing

1. Deploy the Data Analysis Pipeline workflow
2. Send a message with data that triggers chart generation
3. Verify:
   - Code blocks show syntax-highlighted Python
   - stdout/stderr display correctly
   - Chart PNGs appear inline below the code output
   - Images are clickable (modal fullscreen) and downloadable
4. Refresh the page and verify images persist from history
