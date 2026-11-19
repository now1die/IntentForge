"""Final cases authored after freezing the implementation and selection policy."""
from .ml_v3_data import A, C, D, F, M, V, X, control, repair
from .phase35_data import FINAL, store

EXERCISM = "https://github.com/exercism/c/blob/1675b02c310198e9752e516ee1a2294b76a37f84"


def external(slug, *args):
    row = repair(*args, kind="logic")
    return {**row, "provenance": "Original Mini-C adaptation of an Exercism task description",
            "external_task": f"{EXERCISM}/exercises/practice/{slug}/.docs/instructions.md",
            "license": "MIT", "license_url": f"{EXERCISM}/LICENSE"}


def guided(description, expression):
    return {"natural": {"description": description}, "explicit": {"return_expression": expression}}


def build():
    return [
        repair("queued_grid_lower", C, "int grid[19];int fill(int seed,int stride){seed+=stride;for(int at=14;at>-1;at--){grid[at]=seed;seed-=stride;}return grid[4];}",
               "at>-1", "at>=-1", kind="logic"),
        repair("shifted_reverse_store", A, "int lace[14];int weave(int gap){for(int at=13;at>=0;at--){lace[at]=at%gap;gap+=1;}return lace[3];}",
               "lace[at]", "lace[at+1]", kind="logic"),
        repair("shifted_nonzero_start", C, "int samples[17];int collect(int seed){int sum=seed;for(int j=3;j<16;j++){int value=samples[j+1];if(value>0){sum+=value;}else{sum-=value;}}return sum;}",
               "j<16", "j<=16", kind="logic"),
        repair("two_reverse_arrays", X, "int push[9];int pull[7];int load(){for(int a=7;a>-1;a--){push[a]=a*3;}for(int b=6;b>=0;b--){pull[b]=b+1;}return push[6]-pull[2];}",
               "a>-1;a--){push[a]=a*3;}for(int b=6;b>=0;b--){pull[b]",
               "a>=-1;a--){push[a]=a*3;}for(int b=6;b>=0;b--){pull[b-1]", kind="logic"),
        repair("buffer_meter", V, "int meter=2;int process(int cost,int divisor,bool hold){int buffered=cost/meter;if(hold){return buffered-1;}meter+=divisor;return buffered+meter;}",
               "buffered+meter", "buffred+meter"),
        repair("cap_strike", D, "bool record(int mark,int limit){bool okay=mark<limit;while(mark>limit){mark--;limit++;}bool flag=okay;if(flag){return mark>0;}return false;}",
               "flag=okay", "flag=mark"),
        repair("folding_order", F, "float unwind(bool negative,char tag,float level){if(negative){return -level;}return level;}float line(char key,float x,bool reverse){if(x==0){return 0;}return unwind(reverse,key,x);}",
               "unwind(reverse,key,x)", "unwind(x,reverse,key)"),
        repair("measured_loss", M, "float delta(float baseline,float changed,int repeat){float loss=baseline-changed;while(repeat>0){loss/=2;repeat--;}if(loss<0){return 0;}return loss;}",
               "return loss;", "return;"),
        repair("read_cap", A, "int pages[50];int read(int cursor,int retries){for(int step=0;step<retries;step++){if(cursor>49){cursor-=50;}}return pages[cursor];}",
               "pages[cursor]", "pages[0]", kind="logic",
               **guided("return the element of pages at index cursor","pages[cursor]")),
        repair("open_interval", C, "bool limit(int x,int bottom,int top){if(x<0){x=-x;}if(bottom>top){top=bottom+1;}return x>bottom && x<top;}",
               "x>bottom && x<top", "x>=bottom && x<top", kind="logic",
               **guided("return whether x is between bottom and top exclusive","x>bottom && x<top")),
        repair("weighted_base", C, "int charge(int force,int bonus){int sum=force%12; if(bonus<0){bonus*=2;}return sum+(bonus);}",
               "sum+(bonus)", "sum/(bonus)", kind="logic",
               **guided("return the accumulator sum plus bonus","sum+(bonus)")),
        repair("unsupported_description", A, "int deck[20];int deal(int round){int top=round*2; while(top>19){top-=20;}return deck[top];}",
               "deck[top]", "deck[round]", kind="logic",
               **guided("deal the appropriate card using the house strategy","deck[top]")),
        external("binary-search", "binary_search_lower", C,
                 "int ordered[10];int find(int target){int lower=0;int upper=9;while(lower<=upper){int pivot=(lower+upper)/2;if(ordered[pivot]==target){return pivot;}if(ordered[pivot]<target){lower=pivot+1;}else{upper=pivot-1;}}return -1;}",
                 "ordered[pivot]<target", "ordered[pivot]>target"),
        external("hamming", "distance_mismatch", C,
                 "char left[12];char right[12];int dist(int lengths){if(lengths<0 || lengths>12){return -1;}int score=0;for(int k=0;k<lengths;k++){if(left[k]!=right[k]){score++;}}return score;}",
                 "left[k]!=right[k]", "left[k]==right[k]"),
        control("valid_break_after_access", "int lens[15];int inspect(int val){for(int j=9;j>=-1;j--){lens[j]=val+j;if(j==0){break;}val--;}return lens[7];}"),
        control("valid_descending_window", "int tar[16];int sweep(int offset){int out=0;for(int j=12;j>=0;j--){int value=tar[j+1];out+=value-offset;}return out;}"),
        control("valid_loop_exit", "int cue[10];int mute(int cut){for(int k=7;k>=-1;k--){if(k<0){return 0;}cue[k]=cut;cut+=2;}return cue[6];}"),
        control("ambiguous_lost_station", "int next(int current,int alternate,int boundary){if(current*alternate<boundary){return listed;}return boundary-1;}", True),
    ]


if __name__ == "__main__":
    rows = build()
    store(FINAL, {"final": rows})
