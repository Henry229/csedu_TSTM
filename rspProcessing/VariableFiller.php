<?php

use qtism\common\enums\BaseType;
use qtism\common\enums\Cardinality;
use qtism\common\datatypes\files\FileManager;
use qtism\common\datatypes\files\FileSystemFileManager;
use qtism\data\IAssessmentItem;
use qtism\data\state\ResponseDeclaration;
use qtism\data\state\OutcomeDeclaration;
use qtism\runtime\pci\json\Unmarshaller as PciJsonUnmarshaller;
use qtism\runtime\pci\json\UnmarshallingException as PciJsonUnmarshallingException;
use qtism\runtime\common\ResponseVariable;
use qtism\runtime\common\OutcomeVariable;
use qtism\runtime\common\OrderedContainer;


class VariableFiller {

    private $itemRef;

    private $fileManager;

    /**
     * Create a new PciVariableFiller object.
     * VariableFiller constructor.
     * @param IAssessmentItem $itemRef
     * @param FileManager|null $fileManager
     */
    public function __construct(IAssessmentItem $itemRef, FileManager $fileManager = null) {
        $this->setItemRef($itemRef);
        $this->fileManager = ($fileManager === null) ? new FileSystemFileManager() : $fileManager;
    }

    /**
     * Get the item reference the variables you want to fill belong to.
     *
     * @return IAssessmentItem An ExtendedAssessmentItemRef object.
     */
    protected function getItemRef() {
        return $this->itemRef;
    }

    /**
     * Set the item reference the variables you want to fill belong to.
     *
     * @param IAssessmentItem $itemRef An IAssessmentItem object.
     */
    protected function setItemRef(IAssessmentItem $itemRef) {
        $this->itemRef = $itemRef;
    }

    /**
     * Fill the variable $variableName with a correctly transformed $clientSideValue.
     *
     * @param string $variableName The variable identifier you want to fill.
     * @param array $clientSideValue The value received from the client-side representing the value of the variable with identifier $variableName.
     * @return Variable A Variable object filled with a correctly transformed $clientSideValue.
     * @throws OutOfBoundsException If no variable with $variableName is described in the item.
     * @throws OutOfRangeException If the $clientSideValue does not fit the target variable's baseType.
     */
    public function fill($variableName, $clientSideValue) {
        $variableDeclaration = $this->findVariableDeclaration($variableName);

        if ($variableDeclaration === false) {
            $itemId = $this->getItemRef()->getIdentifier();
            $msg = "Variable declaration with identifier '${variableName}' not found in item '${itemId}'.";
            throw new \OutOfBoundsException($msg);
        }

        // Create Runtime Variable from Data Model.
        $runtimeVar = ($variableDeclaration instanceof ResponseDeclaration) ? ResponseVariable::createFromDataModel($variableDeclaration) : OutcomeVariable::createFromDataModel($variableDeclaration);

        // Set the data into the runtime variable thanks to the PCI JSON Unmarshaller
        // from QTISM.
        try {
            $unmarshaller = new PciJsonUnmarshaller($this->fileManager);
            $value = $unmarshaller->unmarshall($clientSideValue);

            // Dev's note:
            // The PCI JSON Representation format does make the difference between multiple and ordered containers.
            // We then have to juggle a bit if the target variable has ordered cardinality.
            if ($value !== null && $value->getCardinality() === Cardinality::MULTIPLE && $variableDeclaration->getCardinality() === Cardinality::ORDERED) {
                $value = new OrderedContainer($value->getBaseType(), $value->getArrayCopy());
            }

            $runtimeVar->setValue($value);
        }
        catch (PciJsonUnmarshallingException $e) {
            $strClientSideValue = mb_substr(var_export($clientSideValue, true), 0, 50, TAO_DEFAULT_ENCODING);
            $msg = "Unable to put value '${strClientSideValue}' into variable '${variableName}'.";
            throw new \OutOfRangeException($msg, 0, $e);
        }

        return $runtimeVar;
    }

    /**
     * Get the OutcomeDeclaration/ResponseDeclaration with identifier $variableIdentifier from
     * the item.
     *
     * @param string $variableIdentifier A QTI identifier.
     * @return \qtism\data\state\VariableDeclaration|boolean The variable with identifier $variableIdentifier or false if it could not be found.
     */
    protected function findVariableDeclaration($variableIdentifier) {
        $responseDeclarations = $this->getItemRef()->getResponseDeclarations();

        if (isset($responseDeclarations[$variableIdentifier]) === true) {
            return $responseDeclarations[$variableIdentifier];
        }
        else {
            $outcomeDeclarations = $this->getItemRef()->getOutcomeDeclarations();

            if (isset($outcomeDeclarations[$variableIdentifier]) === true) {
                return $outcomeDeclarations[$variableIdentifier];
            }
            else {
                // Variable $variableIdentifier not found.
                return false;
            }
        }
    }
}
