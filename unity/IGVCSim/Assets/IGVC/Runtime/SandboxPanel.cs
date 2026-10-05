using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.UIElements;

namespace IGVC
{
    // UI owns draft/course editing; ROS supervisor owns navigation and lifecycle.
    public sealed class SandboxPanel : MonoBehaviour
    {
        private TransportProbe probe;
        private SpectatorCamera spectator;
        private Camera view;
        private string directory,selectedId,placement="select",pendingId="",presetName="My course",tab="course";
        private UIDocument document;
        private PanelSettings panelSettings;
        private VisualElement root,sidebar,content,runControls,marker;
        private Label statusLabel,selectionLabel;
        private readonly List<VisualElement> editableControls=new List<VisualElement>();
        private readonly Stack<string> undo=new Stack<string>();
        private SandboxPreset draft;
        private SandboxStatus status=new SandboxStatus {state="offline"};
        private double nextStatus;
        private bool visible=true,editable,waiting,initialized;
        private Button startButton,stopButton;
        private string notice="Select an obstacle or choose Add, then click the ground.";
        private IGVC.Reference.ReferenceLab lab;
        private Label refStatus,refDetail;
        private CourseVariant.Obstacle Selected => draft.course.obstacles.FirstOrDefault(o=>o.id==selectedId);
        public void Initialize(TransportProbe owner,string path)
        {
            probe=owner;directory=Path.GetFullPath(path);Directory.CreateDirectory(directory);
            draft=new SandboxPreset {course=SandboxDocument.Clone(owner.ActiveVariant)};
            spectator=FindFirstObjectByType<SpectatorCamera>();view=spectator.GetComponent<Camera>();spectator.ShowControls=false;
            probe.SandboxHold(true);
            panelSettings=ScriptableObject.CreateInstance<PanelSettings>();
            panelSettings.themeStyleSheet=Resources.Load<ThemeStyleSheet>("SandboxTheme");
            panelSettings.scaleMode=PanelScaleMode.ConstantPixelSize;
            document=gameObject.AddComponent<UIDocument>();document.panelSettings=panelSettings;document.sortingOrder=50;
            Resources.Load<VisualTreeAsset>("SandboxPanel").CloneTree(document.rootVisualElement);
            root=document.rootVisualElement;root.style.flexGrow=1;
            root.style.unityFontDefinition=FontDefinition.FromFont(Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"));
            sidebar=root.Q("sidebar");content=root.Q("content");statusLabel=root.Q<Label>("status");
            runControls=root.Q("runControls");
            var scroll=(ScrollView)content;scroll.horizontalScrollerVisibility=ScrollerVisibility.Hidden;
            scroll.verticalScroller.lowButton.text="▲";scroll.verticalScroller.highButton.text="▼";
            root.Q<Button>("courseTab").clicked+=()=>SwitchTab("course");
            root.Q<Button>("navTab").clicked+=()=>SwitchTab("nav");
            root.Q<Button>("refTab").clicked+=()=>SwitchTab("reference");
            root.Q<Button>("togglePanel").clicked+=TogglePanel;
            root.Q<Button>("overview").clicked+=ShowCourse;
            root.Q<Button>("follow").clicked+=()=>spectator.SetFollow(true);
            // Audit-only studies of the WORLD course; never connected to ROS or mission inputs.
            lab=gameObject.AddComponent<IGVC.Reference.ReferenceLab>();lab.Initialize(probe);
            marker=new Label("SELECTED");marker.AddToClassList("selection-marker");marker.pickingMode=PickingMode.Ignore;root.Add(marker);
            BuildContent();initialized=true;root.RegisterCallback<GeometryChangedEvent>(_=>LayoutView());
            root.schedule.Execute(()=>{LayoutView();ShowCourse();}).StartingIn(100);
            if(Environment.GetCommandLineArgs().Contains("--sandbox-smoke"))StartCoroutine(Smoke());
            var args=Environment.GetCommandLineArgs();int batchArg=Array.IndexOf(args,"--sandbox-batch");
            if(batchArg>=0&&batchArg+1<args.Length)StartCoroutine(Batch(args[batchArg+1]));
        }
        private void SwitchTab(string value)
        {
            tab=value;BuildContent();
            root.Q<Button>("courseTab").EnableInClassList("active-tab",tab=="course");
            root.Q<Button>("navTab").EnableInClassList("active-tab",tab=="nav");
            root.Q<Button>("refTab").EnableInClassList("active-tab",tab=="reference");
        }
        private void TogglePanel(){visible=!visible;sidebar.style.display=visible?DisplayStyle.Flex:DisplayStyle.None;root.Q<Button>("togglePanel").text=visible?"Hide panel [F1]":"Show panel [F1]";root.schedule.Execute(LayoutView);}
        private void LayoutView()
        {
            float left=visible?480f/Screen.width:0, bottom=58f/Screen.height,top=76f/Screen.height;
            view.rect=new Rect(left,bottom,Mathf.Max(.1f,1-left),Mathf.Max(.1f,1-bottom-top));
        }
        private void ShowCourse()
        {
            var bounds=new Bounds(new Vector3((float)-draft.course.centerline[0].y,0,(float)draft.course.centerline[0].x),Vector3.zero);
            foreach(var p in draft.course.centerline)bounds.Encapsulate(new Vector3((float)-p.y,0,(float)p.x));
            bounds.Expand(5);spectator.FrameOverview(bounds);
        }
        private void Title(string text){var label=new Label(text);label.AddToClassList("section");content.Add(label);}
        private void Hint(string text){var label=new Label(text);label.AddToClassList("hint");content.Add(label);}
        private VisualElement Row(){var row=new VisualElement();row.AddToClassList("row");content.Add(row);return row;}
        private Button Button(VisualElement parent,string text,Action action,bool edit=true,string css=null)
        {
            var b=new Button(()=>Attempt(action)){text=text};if(css!=null)b.AddToClassList(css);parent.Add(b);
            if(edit)editableControls.Add(b);return b;
        }
        private FloatField Number(string label,double value,Action<double> change)
        {
            var field=new FloatField(label){value=(float)value,isDelayed=true};
            field.RegisterValueChangedCallback(e=>{if(editable)change(e.newValue);});content.Add(field);editableControls.Add(field);return field;
        }
        private DropdownField Dropdown(string label,List<string> choices,string value,Action<string> change)
        {
            var field=new DropdownField(label,choices,Math.Max(0,choices.IndexOf(value)));
            field.RegisterValueChangedCallback(e=>{if(editable)change(e.newValue);});content.Add(field);editableControls.Add(field);return field;
        }
        private void BuildContent()
        {
            content.Clear();runControls.Clear();editableControls.Clear();
            if(tab=="course")
            {
                Title("1 / Place obstacles");Hint("Choose a type, then click the ground. Right-drag orbits; middle-drag pans; wheel zooms.");
                var row=Row();foreach(string kind in new[]{"barrel","barricade","pothole"})
                    Button(row,"+ "+kind,()=>{placement=kind;notice="Click the ground to place a "+kind+".";});
                var actions=Row();Button(actions,"Select",()=>{placement="select";notice="Click an obstacle to select it.";});
                Button(actions,"Move selected",()=>{if(Selected==null)throw new InvalidOperationException("Select an obstacle first.");placement="move";notice="Click the destination on the ground.";});
                Title("2 / Selected obstacle");selectionLabel=new Label(Selected==null?"Nothing selected":Selected.kind+" / "+Selected.id);selectionLabel.AddToClassList("hint");content.Add(selectionLabel);
                if(Selected!=null)
                {
                    var values=SandboxDocument.Clone(Selected);
                    Number("Forward position (m)",values.x,v=>values.x=v);Number("Left position (m)",values.y,v=>values.y=v);
                    Number("Rotation (degrees)",values.yaw*Mathf.Rad2Deg,v=>values.yaw=v*Mathf.Deg2Rad);
                    Number("Length (m)",values.length,v=>values.length=v);Number("Width (m)",values.width,v=>values.width=v);
                    if(values.kind=="pothole")Number("Depression depth (m)",values.depth,v=>values.depth=v);
                    else Number("Height (m)",values.height,v=>values.height=v);
                    if(values.kind=="barrel")Dropdown("Barrel color",new List<string>{"orange","red","blue","green","yellow","white"},values.color,v=>values.color=v);
                    var edit=Row();Button(edit,"Apply changes",()=>Change(m=>m.obstacles[Array.FindIndex(m.obstacles,o=>o.id==selectedId)]=values),true,"primary");
                    Button(edit,"Delete",()=>Change(m=>m.obstacles=m.obstacles.Where(o=>o.id!=selectedId).ToArray()),true,"danger");
                }
                var history=Row();Button(history,"Undo edit",Undo);Button(history,"Reset course",()=>Change(_=>draft.course=CourseVariant.Read(Path.Combine(directory,"baseline-course.json")))) ;
                Title("3 / Save your experiment");
                var name=new TextField("Preset name"){value=presetName,isDelayed=true};name.RegisterValueChangedCallback(e=>presetName=e.newValue);content.Add(name);editableControls.Add(name);
                string presets=Path.Combine(directory,"presets");
                if(Directory.Exists(presets)) {
                    var names=Directory.GetFiles(presets,"*.json").Select(Path.GetFileNameWithoutExtension).OrderBy(n=>n).ToList();
                    if(names.Count>0)Dropdown("Saved presets",names,presetName,v=>{presetName=v;name.SetValueWithoutNotify(v);});
                }
                var saves=Row();Button(saves,"Save preset",SavePreset);Button(saves,"Load preset",LoadPreset);
                Hint("Presets include obstacles and navigation settings. Enter a saved name to load it. Existing names are overwritten. The baseline course stays separate.");
            }
            else if(tab=="reference")BuildReference();
            else
            {
                Title("Navigation experiment");Hint("Settings apply on the next Start. Algorithm changes are experiments; the 6/6 result used RPP + checked path at 0.6 m/s.");
                Dropdown("Controller",new List<string>{"rpp","mppi"},draft.settings.controller,v=>{draft.settings.controller=v;BuildContent();});
                Hint(draft.settings.controller=="rpp"?"RPP: follows the checked path using a lookahead target.":"MPPI: samples motion trajectories and scores their costs.");
                Dropdown("Path execution",new List<string>{"checked-path","nav2-goal"},draft.settings.execution,v=>draft.settings.execution=v);
                Hint("Checked path: custom observed-space search. Nav2 goal: Nav2 replans toward the selected local target.");
                Dropdown("Escape from traps",new List<string>{"legacy","retrace"},draft.settings.escape,v=>draft.settings.escape=v);
                Hint("Legacy: short straight checked backup (the 6/6 baseline). Retrace: remembers where it got stuck and may back out along its own observed path. Experimental.");
                Number("Learned route weight",draft.settings.route_weight,v=>draft.settings.route_weight=v);
                Number("Learned corridor weight",draft.settings.corridor_weight,v=>draft.settings.corridor_weight=v);
                Hint("0 = off (baseline). Above 0, the promoted models learned from simulated runs re-rank only already-safe options; they never see the course map.");
                Number("Speed ceiling (m/s)",draft.settings.speed_mps,v=>draft.settings.speed_mps=v);
                Number("Inflation radius (m)",draft.settings.inflation_m,v=>draft.settings.inflation_m=v);
                Number("Clearance preference",draft.settings.clearance_weight,v=>draft.settings.clearance_weight=v);
                Number("Planning budget (s)",draft.settings.planning_budget_s,v=>draft.settings.planning_budget_s=v);
                if(draft.settings.controller=="rpp")Number("RPP lookahead (m)",draft.settings.lookahead_m,v=>draft.settings.lookahead_m=v);
                Button(content,"Restore successful 6/6 settings",()=>{draft.settings=new SandboxSettings();BuildContent();});
                Hint("Footprint collision checks remain enabled. The robot receives six broad destinations, not the obstacle layout. Edited courses may be impossible to complete.");
            }
            var runTitle=new Label("Run controls");runTitle.AddToClassList("section");runControls.Add(runTitle);
            var run=new VisualElement();run.AddToClassList("row");runControls.Add(run);startButton=Button(run,"Start from beginning",StartRun,true,"primary");
            stopButton=Button(run,"Stop trial",StopRun,false,"danger");
            var runHint=new Label("Stop to edit. Start resets the robot and its observations.");runHint.AddToClassList("hint");runControls.Add(runHint);
            ApplyEnabled();
        }
        private Toggle Check(string label,bool value,Action<bool> change,bool edit)
        {
            var toggle=new Toggle(label){value=value};toggle.RegisterValueChangedCallback(e=>Attempt(()=>change(e.newValue)));
            content.Add(toggle);if(edit)editableControls.Add(toggle);return toggle;
        }
        private void Table(IEnumerable<string> lines)
        {
            var text=string.Join("\n",lines??Enumerable.Empty<string>());if(text.Length==0)return;
            var label=new Label(text);label.AddToClassList("ref-table");content.Add(label);
        }
        private static readonly string[] AlgoNames={"HPA*","JPS","A*","Weighted A*","Bidirectional A*","Dijkstra","Flow field"};
        private static readonly IGVC.Reference.Pathfinding.Algo[] AlgoValues={IGVC.Reference.Pathfinding.Algo.Hpa,IGVC.Reference.Pathfinding.Algo.Jps,IGVC.Reference.Pathfinding.Algo.AStar,IGVC.Reference.Pathfinding.Algo.WeightedAStar,IGVC.Reference.Pathfinding.Algo.BidirAStar,IGVC.Reference.Pathfinding.Algo.Dijkstra,IGVC.Reference.Pathfinding.Algo.FlowField};
        private bool referenceWasBusy;
        // Planner, line and ghost studies read the WORLD course for review only; compute buttons follow the
        // edit lock so a study never loads the main thread during a trial.
        private void BuildReference()
        {
            var l=lab;var paths=l.Paths;var line=l.Line;
            Title("Reference lab");
            var warning=new Label("Uses the full course file. Results are a reference for review: the robot never receives them, and ghosts are invisible to its sensors.");
            warning.AddToClassList("ref-warning");content.Add(warning);
            refStatus=new Label(l.Status);refStatus.AddToClassList("hint");content.Add(refStatus);
            Title("1 / Grid planner");Hint("Lane and obstacles rasterised at 0.1 m and grown by the robot half-width. Route: one lap from the start line.");
            Dropdown("Algorithm",AlgoNames.ToList(),AlgoNames[Array.IndexOf(AlgoValues,paths.Algorithm)],v=>{paths.Algorithm=AlgoValues[Array.IndexOf(AlgoNames,v)];BuildContent();});
            if(paths.Algorithm==IGVC.Reference.Pathfinding.Algo.Hpa)
            {
                Dropdown("Cluster size (cells)",new List<string>{"8","16","32","64"},paths.ClusterSize.ToString(),v=>paths.ClusterSize=int.Parse(v));
                Check("Smooth refined path",paths.Smooth,v=>paths.Smooth=v,true);
            }
            if(paths.Algorithm==IGVC.Reference.Pathfinding.Algo.WeightedAStar)Number("Heuristic weight",paths.Weight,v=>{if(v<1||v>5)throw new InvalidDataException("Weight must be between 1 and 5.");paths.Weight=v;});
            var plan=Row();Button(plan,"Plan route",l.PlanRoute,true,"primary");Button(plan,"Benchmark 200 pairs",()=>l.Benchmark(200));
            var view=l.PathView;
            Check("Grid",view.ShowGrid,v=>{view.ShowGrid=v;view.Draw(paths);},false);
            Check("Clusters",view.ShowClusters,v=>{view.ShowClusters=v;view.Draw(paths);},false);
            Check("Entrances",view.ShowEntrances,v=>{view.ShowEntrances=v;view.Draw(paths);},false);
            Check("Abstract graph",view.ShowAbstractGraph,v=>{view.ShowAbstractGraph=v;view.Draw(paths);},false);
            Check("Search expansions",view.ShowExpansions,v=>{view.ShowExpansions=v;view.Draw(paths);},false);
            Check("Path",view.ShowPath,v=>{view.ShowPath=v;view.Draw(paths);},false);
            Table(paths.Summary());
            Table(paths.Rows.Select(r=>r.Entry.Name+": "+r.AvgMs.ToString("0.00")+" ms, "+r.AvgExpanded.ToString("0")+" expanded, gap "+r.AvgGap.ToString("0.00")+"% (max "+r.MaxGap.ToString("0.0")+"%), "+r.Found+"/"+r.Queries+" found"));
            Title("2 / Racing line");
            var methods=Enum.GetNames(typeof(IGVC.Reference.RacingLine.LineMethod)).ToList();
            Dropdown("Method",methods,line.Method.ToString(),v=>line.Method=(IGVC.Reference.RacingLine.LineMethod)Enum.Parse(typeof(IGVC.Reference.RacingLine.LineMethod),v));
            Number("Speed ceiling (m/s)",line.SpeedCeiling,v=>{if(v<.1||v>2.2)throw new InvalidDataException("Speed ceiling must be between 0.1 and 2.2 m/s.");line.SpeedCeiling=v;});
            Check("Pass obstacles on the planner's side",l.UseRoute,v=>l.UseRoute=v,true);
            var optimise=Row();Button(optimise,"Optimise line",l.OptimiseLine,true,"primary");Button(optimise,"Compare all methods",l.CompareLines);
            Hint("Lap time is a lower bound under assumed limits (accel 0.8, brake 1.2, lateral 1.0 m/s²) plus the wheel-speed limit; not calibrated hardware.");
            Table(line.Summary());
            if(line.Comparison.Count>1)Table(line.Comparison.Select(r=>r.Name+": "+r.LapTime.ToString("0.0")+" s, "+r.Length.ToString("0.0")+" m, max |k| "+r.MaxKappa.ToString("0.00")+", body contacts "+r.FootprintContacts+", "+r.Millis.ToString("0")+" ms"));
            Title("3 / AI driver ghosts");
            Hint("Pure pursuit (like Nav2 RPP), Stanley, sampling MPC and a neural range-sensor driver follow the line with differential-drive limits.");
            var ghosts=Row();Button(ghosts,"Start ghosts",l.StartGhosts,false,"primary");Button(ghosts,"Stop",l.StopGhosts,false);
            var speed=Row();foreach(double factor in new[]{1.0,4.0,16.0})Button(speed,factor+"x speed",()=>l.GhostSpeed=factor,false);
            Button(content,"Train neural driver (20 generations)",()=>l.TrainNeural(20));
            Title("4 / Compare the real robot");
            Check("Record robot trail",l.RecordTrail,v=>l.RecordTrail=v,false);
            var trail=Row();Button(trail,"Clear trail",l.ClearTrail,false);Button(trail,"Cancel study",l.Cancel,false,"danger");
            Check("Show reference drawings",l.DrawingsVisible,l.SetVisible,false);
            refDetail=new Label("");refDetail.AddToClassList("ref-table");content.Add(refDetail);
            RefreshReference();
        }
        private void RefreshReference()
        {
            if(lab==null)return;
            bool finished=referenceWasBusy&&!lab.Busy;referenceWasBusy=lab.Busy;
            if(tab!="reference"||refStatus==null)return;
            if(finished){BuildContent();return;}
            refStatus.text=lab.Status;
            var lines=new List<string>();
            if(lab.Drivers!=null)lines.AddRange(lab.Drivers.Summary());
            if(lab.RecordTrail||lab.TrailContacts>0||lab.TrailMaxDeviation>0)
                lines.Add("Robot trail: deviation from line mean "+lab.TrailMeanDeviation.ToString("0.00")+" m, max "+lab.TrailMaxDeviation.ToString("0.00")+" m; reference footprint contacts "+lab.TrailContacts);
            refDetail.text=string.Join("\n",lines);
        }
        private void Attempt(Action operation)
        {try{operation();}catch(Exception e){notice=e.Message;Debug.LogWarning("Sandbox: "+e.Message);}}
        private void RequireEdit(){if(!editable)throw new InvalidOperationException("Wait for the session to stop before editing.");}
        private void Change(Action<CourseVariant.Manifest> mutation)
        {
            RequireEdit();string previous=JsonUtility.ToJson(draft);
            try {mutation(draft.course);Commit();undo.Push(previous);if(undo.Count>30){var kept=undo.Take(30).Reverse().ToArray();undo.Clear();foreach(var entry in kept)undo.Push(entry);}BuildContent();}
            catch {draft=JsonUtility.FromJson<SandboxPreset>(previous);throw;}
        }
        private void Commit()
        {
            SandboxDocument.ValidateSettings(draft.settings);SandboxDocument.ValidateEdit(draft.course);
            string candidate=Path.Combine(directory,"candidate-course.json");
            SandboxDocument.AtomicWrite(candidate,JsonUtility.ToJson(draft.course,true));
            CourseVariant.Read(candidate);
            string coursePath=Path.Combine(directory,"course.json"),previous=File.ReadAllText(coursePath);
            SandboxDocument.AtomicWrite(coursePath,File.ReadAllText(candidate));
            try {probe.SandboxReload(coursePath);}
            catch {SandboxDocument.AtomicWrite(coursePath,previous);throw;}
            draft.course=SandboxDocument.Clone(probe.ActiveVariant);notice="Course updated. "+draft.course.obstacles.Length+" obstacles. Start begins a fresh trial.";
        }
        private void Undo()
        {
            RequireEdit();if(undo.Count==0){notice="Nothing to undo.";return;}
            var before=draft;draft=JsonUtility.FromJson<SandboxPreset>(undo.Peek());
            try{Commit();undo.Pop();BuildContent();}catch{draft=before;throw;}
        }
        private void SavePreset()
        {
            RequireEdit();SandboxDocument.ValidateSettings(draft.settings);
            SandboxDocument.AtomicWrite(SandboxDocument.PresetPath(directory,presetName),JsonUtility.ToJson(draft,true));
            notice="Saved '"+presetName+"' in "+Path.Combine(directory,"presets");
        }
        private void LoadPreset()
        {
            RequireEdit();var path=SandboxDocument.PresetPath(directory,presetName);
            if(!File.Exists(path))throw new FileNotFoundException("No preset named '"+presetName+"'.");
            if(new FileInfo(path).Length>4000000)throw new InvalidDataException("Preset is too large.");
            var loaded=JsonUtility.FromJson<SandboxPreset>(File.ReadAllText(path));
            if(loaded==null||loaded.schema_version!=1)throw new InvalidDataException("Unsupported preset version.");
            string previous=JsonUtility.ToJson(draft);draft=loaded;
            try{Commit();undo.Push(previous);selectedId=null;BuildContent();}catch{draft=JsonUtility.FromJson<SandboxPreset>(previous);throw;}
        }
        private void StartRun()
        {
            RequireEdit();SandboxDocument.ValidateSettings(draft.settings);
            // A planner/line study must not keep loading the main thread during a trial.
            lab.Cancel();
            placement="select";Send("start");probe.SandboxHold(false);notice="Starting a fresh trial with the selected settings...";
        }
        private void StopRun(){probe.SandboxHold(true);Send("stop");notice="Stopping navigation; editing unlocks after confirmation.";}
        private void Send(string action)
        {
            pendingId=Guid.NewGuid().ToString("N");waiting=true;editable=false;
            SandboxDocument.AtomicWrite(Path.Combine(directory,"command.json"),JsonUtility.ToJson(new SandboxCommand{id=pendingId,action=action,settings=draft.settings}));ApplyEnabled();
        }
        private void ApplyEnabled(){foreach(var control in editableControls)control.SetEnabled(editable);if(stopButton!=null)stopButton.SetEnabled(true);}
        private void Update()
        {
            if(!initialized)return;
            // Constant pixel size keeps controls readable, including on smaller windows.
            if(Input.GetKeyDown(KeyCode.F1))TogglePanel();
            var mouse=new Vector2(Input.mousePosition.x,Screen.height-Input.mousePosition.y);
            bool overUI=(visible&&sidebar.worldBound.Contains(mouse))||root.Q("topbar").worldBound.Contains(mouse)||statusLabel.worldBound.Contains(mouse);
            bool focused=false;
            for(var element=root.focusController?.focusedElement as VisualElement;element!=null;element=element.parent)
                if(element.ClassListContains("unity-base-field")){focused=true;break;}
            spectator.InputBlocked=overUI||focused;
            if(Time.realtimeSinceStartupAsDouble>=nextStatus)
            {
                nextStatus=Time.realtimeSinceStartupAsDouble+.25;
                try{ReadStatus();}catch(Exception e){editable=false;probe.SandboxHold(true);status.state="offline";notice="Invalid session status: "+e.Message;ApplyEnabled();}
                statusLabel.text=status.state.ToUpperInvariant()+"  |  "+status.completed_destinations+" / 6  |  "+notice;
                RefreshReference();
            }
            if(editable&&!overUI&&!focused&&Input.GetMouseButtonDown(0))Attempt(()=>WorldClick());
            marker.style.display=DisplayStyle.None;
            if(Selected!=null)
            {
                var p=view.WorldToScreenPoint(new Vector3((float)-Selected.y,(float)Selected.height+.3f,(float)Selected.x));
                if(p.z>0){marker.style.display=DisplayStyle.Flex;marker.style.left=p.x-55;marker.style.top=Screen.height-p.y-20;}
            }
        }
        private void ReadStatus()
        {
            string path=Path.Combine(directory,"status.json");
            if(!File.Exists(path)||(DateTime.UtcNow-File.GetLastWriteTimeUtc(path)).TotalSeconds>3)
            {editable=false;probe.SandboxHold(true);status.state="offline";notice="Session unavailable. Use the IGVC Sandbox launcher.";ApplyEnabled();return;}
            string statusText;
            using(var stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))
            using(var reader=new StreamReader(stream))statusText=reader.ReadToEnd();
            var next=JsonUtility.FromJson<SandboxStatus>(statusText);
            if(next==null||!new[]{"idle","starting","running","stopping","completed","error"}.Contains(next.state))
                throw new InvalidDataException("Unrecognized session state.");
            status=next;
            if(waiting&&next.id==pendingId)waiting=false;
            editable=!waiting&&status.editable&&(status.state=="idle"||status.state=="completed");
            if(editable||status.state=="error")probe.SandboxHold(true);
            if(status.state=="error")notice=status.message;
            ApplyEnabled();
        }
        private void WorldClick()
        {
            var ray=view.ScreenPointToRay(Input.mousePosition);
            if(placement=="select")
            {
                if(Physics.Raycast(ray,out var hit,300))selectedId=hit.collider.GetComponentInParent<SandboxObstacle>()?.Id;
                BuildContent();return;
            }
            if(!new Plane(Vector3.up,Vector3.zero).Raycast(ray,out float distance))return;
            var point=ray.GetPoint(distance);double x=Math.Round(point.z*4)/4,y=Math.Round(-point.x*4)/4;
            if(placement=="move")Change(m=>{var o=Selected;o.x=x;o.y=y;});
            else
            {
                string kind=placement;selectedId="edit-"+Guid.NewGuid().ToString("N").Substring(0,10);
                Change(m=>{var list=m.obstacles.ToList();list.Add(new CourseVariant.Obstacle{id=selectedId,kind=kind,color="orange",x=x,y=y,length=kind=="barricade"?1.6:kind=="pothole"?.9:.6,width=kind=="barricade"?.18:kind=="pothole"?.9:.6,height=kind=="pothole"?0:.9,depth=kind=="pothole"?.15:0});m.obstacles=list.ToArray();});
            }
            placement="select";
        }
        [Serializable] private sealed class BatchSpec { public string arm="baseline",difficulty="normal"; public int seed; public SandboxSettings settings=new SandboxSettings(); }
        [Serializable] private sealed class BatchPlan { public int schema_version; public string[] arms; public BatchSpec[] trials; public double trial_timeout_s=720; }
        [Serializable] private sealed class BatchTrial
        {
            public int index,seed; public string arm,difficulty,controller,execution,escape,run,state,message,start_utc; public double speed_mps,route_weight,corridor_weight;
            public int completed_destinations,frames,ghost_laps;
            public double wall_s,frame_ms_mean,frame_ms_p95,frame_ms_p99,frame_ms_max,trail_mean_deviation_m,trail_max_deviation_m;
            public int trail_reference_contacts;
            public bool infrastructure_retry;
        }
        [Serializable] private sealed class RunReason { public string reason; public int completed_destinations; }
        [Serializable] private sealed class BatchResult { public int schema_version=1; public string plan,started_utc,finished_utc,state="running"; public List<BatchTrial> trials=new List<BatchTrial>(); }
        // Unattended sequential trials through the same Start/Stop protocol as the buttons. Arm "reference-load"
        // runs the Reference Lab during the trial (looping ghosts, trail, drawings) to measure its cost.
        private static string BatchCourse(string planPath,BatchSpec spec,string name)=>Path.Combine(Path.GetDirectoryName(Path.GetFullPath(planPath)),"courses",spec.seed+"-"+spec.difficulty,name);
        private IEnumerator Batch(string planPath)
        {
            var plan=JsonUtility.FromJson<BatchPlan>(File.ReadAllText(planPath));
            var result=new BatchResult{plan=Path.GetFullPath(planPath),started_utc=DateTime.UtcNow.ToString("o")};
            string output=Path.Combine(Path.GetDirectoryName(Path.GetFullPath(planPath)),"batch-results.json");
            void Save()=>SandboxDocument.AtomicWrite(output,JsonUtility.ToJson(result,true));
            // "arms" (seed 0 = the session's layout, accepted settings) or explicit "trials" with seed/difficulty/settings.
            var specs=plan?.trials!=null&&plan.trials.Length>0?plan.trials:plan?.arms?.Select(a=>new BatchSpec{arm=a}).ToArray();
            string invalid=null;
            if(plan==null||plan.schema_version!=1||specs==null||specs.Length==0)invalid="invalid plan";
            else foreach(var s in specs)
            {
                if(s.arm!="baseline"&&s.arm!="reference-load")invalid="unknown arm "+s.arm;
                else if(s.seed!=0&&!File.Exists(BatchCourse(planPath,s,"course.json")))invalid="missing generated course for seed "+s.seed+" "+s.difficulty;
                else try{SandboxDocument.ValidateSettings(s.settings);}catch(Exception e){invalid=e.Message;}
            }
            if(invalid!=null){result.state=invalid;Save();Application.Quit();yield break;}
            // The session's own layout and mission, restored for seed-0 trials.
            string defaultCourse=Path.Combine(directory,"baseline-course.json"),defaultMission=Path.Combine(Path.GetDirectoryName(Path.GetFullPath(planPath)),"default-autonomy.json");
            File.Copy(Path.Combine(directory,"autonomy.json"),defaultMission,true);
            double deadline=Time.realtimeSinceStartupAsDouble+180;
            while(!(editable&&status.state=="idle")&&Time.realtimeSinceStartupAsDouble<deadline)yield return new WaitForSecondsRealtime(.5f);
            if(!editable){result.state="session never became editable: "+status.state+" "+status.message;Save();Application.Quit();yield break;}
            string runs=Path.Combine(directory,"runs");string loaded=null;
            bool retried=false;
            for(int i=0;i<specs.Length;i++)
            {
                if(status.state=="error"||!editable){StopRun();deadline=Time.realtimeSinceStartupAsDouble+120;while(!(editable&&status.state=="idle")&&Time.realtimeSinceStartupAsDouble<deadline)yield return new WaitForSecondsRealtime(.5f);}
                var spec=specs[i];
                var trial=new BatchTrial{index=i,arm=spec.arm,seed=spec.seed,difficulty=spec.seed==0?"session":spec.difficulty,controller=spec.settings.controller,execution=spec.settings.execution,escape=spec.settings.escape,speed_mps=spec.settings.speed_mps,route_weight=spec.settings.route_weight,corridor_weight=spec.settings.corridor_weight,start_utc=DateTime.UtcNow.ToString("o")};result.trials.Add(trial);
                if(!editable){trial.state="not editable before start: "+status.state;Save();break;}
                string layout=spec.seed==0?"session":spec.seed+"-"+spec.difficulty;
                if(layout!=loaded)
                {
                    // World layout for Unity and the matching sanitized six-goal mission for the supervisor.
                    try{
                        SandboxDocument.AtomicWrite(Path.Combine(directory,"autonomy.json"),File.ReadAllText(spec.seed==0?defaultMission:BatchCourse(planPath,spec,"autonomy.json")));
                        draft.course=CourseVariant.Read(spec.seed==0?defaultCourse:BatchCourse(planPath,spec,"course.json"));Commit();undo.Clear();selectedId=null;loaded=layout;
                    }catch(Exception e){trial.state="layout load failed: "+e.Message;Save();break;}
                    // Let the reloaded world and its streams settle before Nav2 restarts for the trial.
                    yield return new WaitForSecondsRealtime(5);
                }
                draft.settings=spec.settings;
                bool load=trial.arm=="reference-load";
                if(load&&(lab.Line==null||lab.Line.Line==null))
                    foreach(Action step in new Action[]{lab.PlanRoute,lab.OptimiseLine})
                    {Attempt(step);while(lab.Busy)yield return null;}
                lab.ClearTrail();lab.RecordTrail=load;lab.SetVisible(load);lab.StopGhosts();
                var before=new HashSet<string>(Directory.Exists(runs)?Directory.GetDirectories(runs).Select(Path.GetFileName):Enumerable.Empty<string>());
                Attempt(StartRun);if(load)Attempt(lab.StartGhosts);
                double started=Time.realtimeSinceStartupAsDouble;var frames=new List<float>();
                while(true)
                {
                    yield return null;frames.Add(Time.unscaledDeltaTime*1000f);
                    if(load&&lab.Drivers!=null&&!lab.GhostsRunning){trial.ghost_laps++;Attempt(lab.StartGhosts);}
                    // Once the supervisor acknowledges our command id, any terminal state belongs to this trial.
                    if(!waiting&&(status.state=="completed"||status.state=="error"||status.state=="idle"))break;
                    if(Time.realtimeSinceStartupAsDouble-started>plan.trial_timeout_s){trial.message="batch timeout; stopped";StopRun();break;}
                }
                lab.StopGhosts();lab.RecordTrail=false;
                trial.wall_s=Time.realtimeSinceStartupAsDouble-started;trial.state=status.state;trial.completed_destinations=status.completed_destinations;
                if(string.IsNullOrEmpty(trial.message))trial.message=status.message;
                trial.run=Directory.Exists(runs)?Directory.GetDirectories(runs).Select(Path.GetFileName).Where(n=>!before.Contains(n)).OrderBy(n=>n).LastOrDefault():null;
                frames.Sort();trial.frames=frames.Count;
                if(frames.Count>0){trial.frame_ms_mean=frames.Average();trial.frame_ms_p95=frames[(int)(frames.Count*.95)];trial.frame_ms_p99=frames[(int)(frames.Count*.99)];trial.frame_ms_max=frames[frames.Count-1];}
                trial.trail_mean_deviation_m=lab.TrailMeanDeviation;trial.trail_max_deviation_m=lab.TrailMaxDeviation;trial.trail_reference_contacts=lab.TrailContacts;
                // A trial that never started driving because a stream or Nav2 was not ready is an
                // infrastructure failure, not navigation evidence: record it and repeat it once.
                string reason=null;
                try{if(trial.run!=null)reason=JsonUtility.FromJson<RunReason>(File.ReadAllText(Path.Combine(runs,trial.run,"run.json"))).reason;}catch(Exception){}
                if(!retried&&trial.state=="error"&&trial.completed_destinations==0&&trial.wall_s<120&&reason!=null
                    &&(reason.StartsWith("Missing live")||reason.StartsWith("Nav2 rejected")||reason.StartsWith("Navigation action server unavailable")))
                {trial.infrastructure_retry=true;trial.message="infrastructure failure (repeated once): "+reason;retried=true;i--;}
                else retried=false;
                Save();
                deadline=Time.realtimeSinceStartupAsDouble+120;
                while(waiting&&Time.realtimeSinceStartupAsDouble<deadline)yield return new WaitForSecondsRealtime(.5f);
            }
            if(status.state=="error"){StopRun();deadline=Time.realtimeSinceStartupAsDouble+120;while(status.state!="idle"&&Time.realtimeSinceStartupAsDouble<deadline)yield return new WaitForSecondsRealtime(.5f);}
            result.state="finished";result.finished_utc=DateTime.UtcNow.ToString("o");Save();
            yield return new WaitForSecondsRealtime(2);Application.Quit();
        }
        private IEnumerator Smoke()
        {
            yield return new WaitForSecondsRealtime(3);
            Attempt(()=>{
                // Exercises the same edit/undo/preset paths as the controls.
                editable=true;int count=draft.course.obstacles.Length;
                selectedId=draft.course.obstacles.First(o=>o.kind=="barrel").id;
                double old=Selected.yaw;Change(m=>Selected.yaw=old+.2);Undo();
                if(Math.Abs(Selected.yaw-old)>1e-6)throw new Exception("Undo did not restore obstacle rotation.");
                presetName="smoke-test";SavePreset();LoadPreset();
                if(draft.course.obstacles.Length!=count)throw new Exception("Preset lost obstacles.");
                Change(m=>{var obstacles=m.obstacles.ToList();obstacles.Add(new CourseVariant.Obstacle{id="smoke-barrel",kind="barrel",color="blue",x=10,y=10,length=.6,width=.6,height=.9});obstacles.Add(new CourseVariant.Obstacle{id="smoke-barricade",kind="barricade",x=12,y=10,length=1.6,width=.18,height=.9});obstacles.Add(new CourseVariant.Obstacle{id="smoke-pothole",kind="pothole",x=14,y=10,length=.9,width=.9,depth=.15});m.obstacles=obstacles.ToArray();});
                if(draft.course.obstacles.Length!=count+3)throw new Exception("Add failed.");
                if(!Physics.Raycast(new Vector3(-10,2,14),Vector3.down,out var pit,3)||pit.point.y>-.1f)throw new Exception("Pothole ground was not cut out.");
                Undo();if(draft.course.obstacles.Length!=count)throw new Exception("Undo add failed.");
                string before=File.ReadAllText(Path.Combine(directory,"course.json"));var oldRoot=probe.ActiveVariant.runtime_root;
                bool rejected=false;
                try{Change(m=>m.centerline[1].x=m.centerline[0].x-1);}catch{rejected=true;}
                if(!rejected||File.ReadAllText(Path.Combine(directory,"course.json"))!=before||probe.ActiveVariant.runtime_root!=oldRoot)throw new Exception("Invalid geometry rollback failed.");
                SandboxDocument.AtomicWrite(Path.Combine(directory,"ui-smoke.json"),"{\"passed\":true,\"edit_undo_save_load\":true,\"all_obstacle_types\":true,\"pothole_cutout\":true,\"invalid_geometry_rollback\":true}");
                notice="Editor smoke checks passed. Select an obstacle to customize it.";
            });
            yield return new WaitForSecondsRealtime(1);
            ScreenCapture.CaptureScreenshot(Path.Combine(directory,"sandbox-editor.png"));
            yield return new WaitForSecondsRealtime(1);SwitchTab("nav");
            yield return new WaitForSecondsRealtime(1);ScreenCapture.CaptureScreenshot(Path.Combine(directory,"sandbox-navigation.png"));
            // Reference lab: plan, optimise and drive ghosts through the same entry points as the buttons.
            yield return new WaitForSecondsRealtime(1);SwitchTab("reference");
            string failure=null;double started=Time.realtimeSinceStartupAsDouble;
            foreach(Action step in new Action[]{lab.PlanRoute,lab.OptimiseLine})
            {
                Attempt(step);
                while(lab.Busy&&Time.realtimeSinceStartupAsDouble-started<120)yield return null;
                if(lab.Busy||lab.Status.Contains("failed")){failure=lab.Status;break;}
            }
            bool routed=lab.Paths.Last!=null&&lab.Paths.Last.Found,lined=lab.Line.Line!=null;
            if(failure==null&&routed&&lined){Attempt(lab.StartGhosts);lab.GhostSpeed=16;}
            yield return new WaitForSecondsRealtime(6);
            bool ghosts=lab.Drivers!=null&&lab.GhostsRunning||lab.Drivers!=null&&lab.Drivers.Finished;
            var sensors=FindObjectsByType<Camera>(FindObjectsInactive.Include,FindObjectsSortMode.None).Where(c=>c!=view).ToArray();
            bool hidden=sensors.Length>=2&&sensors.All(c=>(c.cullingMask&IGVC.Reference.ReferenceLayer.Mask)==0);
            if(!hidden)failure="Sensor cameras render the reference layer.";
            lab.StopGhosts();BuildContent();
            yield return new WaitForSecondsRealtime(1);ScreenCapture.CaptureScreenshot(Path.Combine(directory,"sandbox-reference.png"));
            yield return new WaitForSecondsRealtime(1);((ScrollView)content).scrollOffset=new Vector2(0,900);
            yield return new WaitForSecondsRealtime(1);ScreenCapture.CaptureScreenshot(Path.Combine(directory,"sandbox-reference-results.png"));
            SandboxDocument.AtomicWrite(Path.Combine(directory,"ui-smoke-reference.json"),"{\"passed\":"+(failure==null&&routed&&lined&&ghosts?"true":"false")+",\"route\":"+(routed?"true":"false")+",\"line\":"+(lined?"true":"false")+",\"ghosts\":"+(ghosts?"true":"false")+",\"sensor_cameras_exclude_reference\":"+(hidden?"true":"false")+",\"sensor_cameras\":"+sensors.Length+",\"seconds\":"+(Time.realtimeSinceStartupAsDouble-started).ToString("0.0",System.Globalization.CultureInfo.InvariantCulture)+"}");
        }
        private void OnDestroy(){if(spectator!=null){spectator.InputBlocked=false;spectator.ShowControls=true;}if(view!=null)view.rect=new Rect(0,0,1,1);if(panelSettings!=null)Destroy(panelSettings);}
    }
}
