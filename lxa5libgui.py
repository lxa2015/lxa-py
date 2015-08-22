__version__ = "5.1.0"

#------------------------------------------------------------------------------#

# constants for window sizes etc

TREEWIDGET_WIDTH_MIN = 200
TREEWIDGET_WIDTH_MAX = TREEWIDGET_WIDTH_MIN + 50
TREEWIDGET_HEIGHT_MIN = 400

MAIN_WINDOW_WIDTH = 1000
MAIN_WINDOW_HEIGHT = 600

#------------------------------------------------------------------------------#

# configuration, with the "factory settings"

# What programs use what parameters:
#   ngrams.py:    max_word_tokens
#   signature.py: max_word_tokens, min_stem_length, max_affix_length, min_sig_use
#   phon.py:      max_word_tokens
#   tries.py:     max_word_tokens, min_stem_length, min_affix_length, min_sf_pf_count
#   manifold.py   max_word_types, n_neighbors, n_eigenvectors, min_context_use
# (See the individual programs for what these parameters mean.)

CONFIG = {"max_word_tokens": 0, # zero means all word tokens
          "min_stem_length": 4,
          "max_affix_length": 4,
          "min_sig_use": 5,
          "min_affix_length": 1,
          "min_sf_pf_count": 3,
          "n_neighbors": 9,
          "n_eigenvectors": 11,
          "min_context_use": 3,
          "max_word_types": 1000,

          "last_filename": None,
          "filenames_run": list(),

          "language" : "",
          "corpus" : "",
          "datafolder" : "",
         }

CONFIG_FILENAME = "config.json"

#------------------------------------------------------------------------------#

# constants for the various programs

PROGRAMS = {"signature", "ngram", "trie", "phon", "manifold"}

PROGRAM_TO_DESCRIPTION = {
    "ngram": "This program extracts word n-grams.",
    "signature": "This program computes morphological signatures.",
    "phon": "This program extracts phon n-grams and works on phonotactics.",
    "trie": "This program computes tries and successor/predecessor frequencies.",
    "manifold": "This program computes word neighbors.",
}


PROGRAM_TO_PARAMETERS = { # useful to know what parameters each program cares about
    "ngram": ["max_word_tokens"],
    "signature": ["max_word_tokens", "min_stem_length", "max_affix_length", 
                  "min_sig_use"],
    "phon": ["max_word_tokens"],
    "trie": ["max_word_tokens", "min_stem_length", "min_affix_length",
             "min_sf_pf_count"],
    "manifold": ["max_word_types", "n_neighbors", "n_eigenvectors",
                 "min_context_use"],
}

#------------------------------------------------------------------------------#

# string names of lexicon tree objects
# do NOT change the variable names! (strings themselves can be altered though)

WORDLIST = "Wordlist"

WORD_NGRAMS = "Word ngrams"
BIGRAMS = "Bigrams"
TRIGRAMS = "Trigrams"

SIGNATURES = "Signatures"
SIGS_TO_STEMS = "Signatures to stems"
WORDS_TO_SIGS = "Words to signatures"

TRIES = "Tries"
WORDS_AS_TRIES = "Words as tries"
SF_TRIES = "Successor frequencies"
PF_TRIES = "Predecessor frequencies"

PHONOLOGY = "Phonology"
PHONES = "Phones"
BIPHONES = "Biphones"
TRIPHONES = "Triphones"

MANIFOLDS = "Manifolds"
WORD_NEIGHBORS = "Word neighbors"
VISUALIZED_GRAPH = "Visualized graph"

#------------------------------------------------------------------------------#

SHOW_MANIFOLD_HTML = """
<!DOCTYPE html>
<meta charset="utf-8">
<style>

.node {{
  stroke: #fff;
  stroke-width: 1.5px;
}}

.link {{
  stroke: #999;
  stroke-opacity: .6;
}}

</style>
<body>
<script src="d3/d3.min.js"></script>
<script>

var width = {}, height = {};

var color = d3.scale.category20();

var force = d3.layout.force()
    .charge(-50)
    .linkDistance(10)
    .size([width, height]);

var svg = d3.select("body").append("svg")
    .attr("width", width)
    .attr("height", height)
    .append("g")
    .call(d3.behavior.zoom().scaleExtent([0.1, 10]).on("zoom", zooming))
    .append("g");

svg.append("rect")
    .attr("fill-opacity", "0")
    .attr("width", width)
    .attr("height", height);


function zooming() {{
  svg.attr("transform", "translate(" + d3.event.translate + ")scale(" + d3.event.scale + ")");
}};

d3.json("{}", function(error, graph) {{
  if (error) throw error;

  force
      .nodes(graph.nodes)
      .links(graph.links)
      .start();

  var tickLimit = Math.ceil(graph.nodes.length/200)

  var link = svg.selectAll(".link")
      .data(graph.links)
    .enter().append("line")
      .attr("class", "link")
      .style("stroke-width", function(d) {{ return Math.sqrt(d.value); }});

  var node = svg.selectAll(".node")
      .data(graph.nodes)
    .enter().append("circle")
      .attr("class", "node")
      .attr("r", 3)
      .style("fill", function(d) {{ return color(d.group); }})
      .call(force.drag);

  var texts = svg.selectAll("text.label")
    .data(graph.nodes)
    .enter().append("text")
    .attr("class", "label")
    .attr("fill", "black")
    .attr("font-size", "7pt")
    .text(function(d) {{  return d.id;  }});

  node.append("title")
      .text(function(d) {{ return d.name; }});

  var tick = tickLimit;
  force.on("tick", function() {{
//    if (true) {{
    if (tick == tickLimit) {{
        link.attr("x1", function(d) {{ return d.source.x; }})
            .attr("y1", function(d) {{ return d.source.y; }})
            .attr("x2", function(d) {{ return d.target.x; }})
            .attr("y2", function(d) {{ return d.target.y; }});

        node.attr("cx", function(d) {{ return d.x; }})
            .attr("cy", function(d) {{ return d.y; }});

        texts.attr("transform", function(d) {{
            return "translate(" + d.x + "," + d.y + ")";
        }});
        tick = 1;
    }}
    else
        tick++;
  }});
}});

</script>
"""


