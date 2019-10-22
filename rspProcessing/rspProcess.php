<?php

require_once 'VariableFiller.php';
require __DIR__ . '/qti-sdk-php/vendor/autoload.php';

use qtism\common\datatypes\files\FileSystemFileManager;
use qtism\common\enums\BaseType;
use qtism\common\enums\Cardinality;
use qtism\common\datatypes\QtiIdentifier;
use qtism\data\storage\xml\XmlDocument;
use qtism\runtime\common\State;
use qtism\runtime\common\ResponseVariable;
use qtism\runtime\common\MultipleContainer;
use qtism\runtime\tests\AssessmentItemSession;
use qtism\runtime\tests\AssessmentItemSessionException;

if(function_exists('xdebug_disable')) { xdebug_disable(); }
error_reporting(0);

define('TAO_DEFAULT_ENCODING', "UTF-8");

$cardinalityArray = [
    'single' => Cardinality::SINGLE,
    'multiple' => Cardinality::MULTIPLE,
    'ordered' => Cardinality::ORDERED,
    'record' => Cardinality::RECORD
];
$baseTypeArray = [
    'identifier' => BaseType::IDENTIFIER,
    'boolean' => BaseType::BOOLEAN,
    'integer' => BaseType::INTEGER,
    'float' => BaseType::FLOAT,
    'string' => BaseType::STRING,
    'point' => BaseType::POINT,
    'pair' => BaseType::PAIR,
    'directed_pair' => BaseType::DIRECTED_PAIR,
    'duration' => BaseType::DURATION,
    'file' => BaseType::FILE,
    'uri' => BaseType::URI,
    'int_or_identifier' => BaseType::INT_OR_IDENTIFIER,
    'coords' => BaseType::COORDS
];

$result = ["result" => "fail"];
$argument = '';
for ($idx =1; $idx < count($argv); $idx++) {
    $argument .= $argv[$idx];
}
$jsonPayload = json_decode($argument, true);

if ($jsonPayload == null) {
    $result['message'] = "Response details is not given.";
    echo json_encode($result);
    return;
}

if (!file_exists($jsonPayload['qtiFilename'])) {
    $result['message'] = "Qti file does not exist.";
    echo json_encode($result);
    return;
}
$qtiXmlFilename = $jsonPayload['qtiFilename'];

// Instantiate a new QTI XML document, and load a QTI XML document.
$itemDoc = new XmlDocument('2.1');
$itemDoc->load($qtiXmlFilename);

/*
 * A QTI XML document can be used to load various pieces of QTI content such as assessmentItem,
 * assessmentTest, responseProcessing, ... components. Our target is an assessmentItem, which is the
 * root component of our document.
 */
$item = $itemDoc->getDocumentComponent();

/*
 * The item session represents the collected and computed data related to the interactions a
 * candidate performs on a single assessmentItem. As per the QTI specification, "an item session
 * is the accumulation of all attempts at a particular instance of an assessmentItem made by
 * a candidate.
 */
$itemSession = new AssessmentItemSession($item);

// The candidate is entering the item session, and is beginning his first attempt.
$itemSession->beginItemSession();
$variables = array();
$filler = new VariableFiller($item);

// Convert client-side data as QtiSm Runtime Variables.
foreach ($jsonPayload['response'] as $id => $response) {

    try {
        $var  = $filler->fill($id, $response);
        $variables[] = $var;
    }
    catch (OutOfRangeException $e) {
        // A variable value could not be converted, ignore it.
        // Developer's note: QTI Pairs with a single identifier (missing second identifier of the pair) are transmitted as an array of length 1,
        // this might cause problem. Such "broken" pairs are simply ignored.
    }
    catch (OutOfBoundsException $e) {
        // No such identifier found in item.
    }
    catch (Exception $e) {
        echo $e;
    }
}

$result = [
    "result" => "success"
];
try {
    $itemSession->beginAttempt();
}
catch (AssessmentItemSessionException $e) {
    $result['message'] = "beginAttempt : ".$e;
    //echo json_encode($result);
}

/*
 * The candidate is finishing the current attempt, by providing a correct response.
 * ResponseProcessing takes place to produce a new value for the 'SCORE' OutcomeVariable.
 */
try {
    $itemSession->endAttempt(new State($variables));
}
catch (AssessmentItemSessionException $e) {
    $result = [
        "result" => "fail"
    ];
    $result['message'] = "endAttempt : ".$e;
    //echo json_encode($result);
}
$outcomeDeclarations = $item->getOutcomeDeclarations();
$maximumScore = 0;
foreach ($outcomeDeclarations as $outcomeDeclaration) {
    $maximumScore += (float)$outcomeDeclaration->getNormalMaximum();
}
if ($maximumScore <= 0)
    $maximumScore = 1.0;
$result["maxScore"] = $maximumScore;

$responseDeclarations = $item->getResponseDeclarations();
$correctResponses = [];
$cardinality = Cardinality::SINGLE;
foreach ($responseDeclarations as $responseDeclaration) {
    $rsp = $responseDeclaration->getCorrectResponse();
    if ($rsp == null) continue;
    $cardinality = $responseDeclaration->getCardinality();
    foreach ($rsp->getValues() as $value) {
        $correctResponses[] = strval($value->getValue());
    }
}
if ($cardinality == Cardinality::SINGLE && count($correctResponses) == 1) {
    $result['correctResponses'] = $correctResponses[0];
}
else {
    $result['correctResponses'] = json_encode($correctResponses);
}
// The item session variables and their values can be accessed by their identifier.
if ($result['result'] == 'success') {
    $result["numAttempts"] = (int)strval($itemSession['numAttempts']);
    $result["completionStatus"] = strval($itemSession['completionStatus']);
    $result["RESPONSE"] = strval($itemSession['RESPONSE']);
    $result["SCORE"] = (float)strval($itemSession['SCORE']);
}
else {
    $result["numAttempts"] = 1;
    $result["completionStatus"] = strval($itemSession['completionStatus']);
    $result["SCORE"] = 0.0;
}

echo json_encode($result);

// End the current item session.
$itemSession->endItemSession();